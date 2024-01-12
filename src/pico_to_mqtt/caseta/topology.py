import itertools
import logging
from asyncio import Condition
from typing import MutableMapping

from pylutron_caseta.smartbridge import Smartbridge

from pico_to_mqtt.caseta.button_watcher import ButtonTracker
from pico_to_mqtt.caseta.model import ButtonId, PicoRemote, PicoRemoteType
from pico_to_mqtt.config import CasetaConfig

LOGGER = logging.getLogger(__name__)


def default_bridge(caseta_config: CasetaConfig) -> Smartbridge:
    return Smartbridge.create_tls(
        caseta_config.caseta_bridge_hostname,
        caseta_config.path_to_caseta_client_key,
        caseta_config.path_to_caseta_client_cert,
        caseta_config.path_to_caseta_client_ca,
    )


class Topology:
    def __init__(
        self,
        caseta_bridge: Smartbridge,
        shutdown_condition: Condition,
        button_tracker: ButtonTracker,
    ) -> None:
        self._caseta_bridge: Smartbridge = caseta_bridge
        self._shutdown_condition = shutdown_condition
        self._button_tracker = button_tracker
        self._remotes_by_id: MutableMapping[int, PicoRemote] = {}

    async def connect(self) -> None:
        LOGGER.info("connecting to caseta bridge")
        try:
            await self._caseta_bridge.connect()
        except Exception as e:
            LOGGER.error(
                "there was a problem connecting to the caseta smartbridge: %s", e
            )
            async with self._shutdown_condition:
                self._shutdown_condition.notify()
            raise e

        all_buttons = self._caseta_bridge.get_buttons()
        all_devices = self._caseta_bridge.get_devices()
        all_areas = self._caseta_bridge.areas
        buttons_by_remote_id = {
            remote_id: list(buttons)
            for remote_id, buttons in itertools.groupby(
                [button for button in all_buttons.values()],
                lambda b: b["parent_device"],
            )
        }

        for device_id, device in all_devices.items():
            # skip devices that are not remotes
            if device_id not in buttons_by_remote_id.keys():
                continue

            remote_buttons = buttons_by_remote_id[device["device_id"]]
            buttons_by_id: dict[int, ButtonId] = {
                int(button["device_id"]): ButtonId.of_int(button["button_number"])
                for button in remote_buttons
            }

            (_ignored, device_name) = device["name"].split('_')
            area_name = all_areas[device["area"]]["name"]
            device_id_as_int = int(device_id)
            if device["type"] in PicoRemoteType.values():
                device_type = PicoRemoteType.from_str(device["type"])
                self._remotes_by_id[device_id_as_int] = PicoRemote(
                    device_id_as_int,
                    device_type,
                    Topology._as_mqtt_friendly_name(device_name),
                    Topology._as_mqtt_friendly_name(area_name),
                    buttons_by_id,
                )

            else:
                LOGGER.warn(
                    (
                        "device: %s: device type `%s` "
                        "is not a supported pico remote and will be skipped"
                    ),
                    device["name"],
                    device["type"],
                )
        LOGGER.info("done connecting to caseta bridge")

    @staticmethod
    def _as_mqtt_friendly_name(raw_name: str) -> str:
        return raw_name.lower().replace("_", "-").replace(" ", "-")

    def attach_callbacks(self):
        for _remote_id, remote in self._remotes_by_id.items():
            for button_id, button in remote.buttons_by_button_id.items():
                self._caseta_bridge.add_button_subscriber(
                    str(button_id),
                    self._button_tracker.button_event_callback(remote, button),
                )
