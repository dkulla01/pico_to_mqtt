import itertools
import logging
from asyncio import Condition

from pylutron_caseta.smartbridge import Smartbridge

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
        self, caseta_bridge: Smartbridge, shutdown_condition: Condition
    ) -> None:
        self._caseta_bridge: Smartbridge = caseta_bridge
        self._shutdown_condition = shutdown_condition
        self._remotes_by_id: dict[int, PicoRemote] = {}

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

            device_name = device["name"].removesuffix("_Pico")
            device_id_as_int = int(device_id)
            if device["type"] in PicoRemoteType.values():
                device_type = PicoRemoteType.from_str(device["type"])
                self._remotes_by_id[device_id_as_int] = PicoRemote(
                    device_id_as_int, device_type, device_name, buttons_by_id
                )

            else:
                LOGGER.debug(
                    (
                        "device: %s: device type `%s` "
                        "is not a supported pico remote and will be skipped"
                    ),
                    device["name"],
                    device["type"],
                )
        LOGGER.info("done connecting to caseta bridge")
