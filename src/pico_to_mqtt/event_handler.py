import asyncio
import json
import logging
from enum import Enum

import aiomqtt
import attrs

from pico_to_mqtt.caseta.model import ButtonId, PicoRemote

LOGGER = logging.getLogger(__name__)


class ButtonEvent(Enum):
    SINGLE_PRESS_COMPLETED = 0
    LONG_PRESS_ONGOING = 1
    LONG_PRESS_COMPLETED = 3
    DOUBLE_PRESS_COMPLETED = 4


@attrs.frozen
class CasetaEvent:
    remote: PicoRemote
    button_id: ButtonId
    button_event: ButtonEvent


class EventHandler:
    def __init__(
        self,
        context_managed_mqtt_client: aiomqtt.Client,
        shutdown_condition: asyncio.Condition,
    ) -> None:
        self._context_managed_mqtt_client = context_managed_mqtt_client
        self._shutdown_condition = shutdown_condition

    async def handle_event(self, event: CasetaEvent):
        topic = (
            f"picotomqtt/{event.remote.area_name}"
            f"/{event.remote.name}"
            f"/{event.button_id.as_mqtt_topic_friendly_name}"
        )
        payload = {
            "button_id": event.button_id.name,
            "area": event.remote.area_name,
            "action": event.button_event.name,
        }
        payload_str = json.dumps(payload)
        try:
            await self._context_managed_mqtt_client.publish(topic, payload_str)
        except Exception as e:
            LOGGER.error(
                (
                    "encountered an error trying to publish mqtt message. "
                    "topic: %s, message: %s, exception: %s"
                ),
                topic,
                payload_str,
                e,
            )
            async with self._shutdown_condition:
                self._shutdown_condition.notify()
            raise e
