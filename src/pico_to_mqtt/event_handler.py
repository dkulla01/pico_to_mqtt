from enum import Enum

import attrs

from pico_to_mqtt.caseta.model import ButtonId, PicoRemote


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
    async def handle_event(self, event: CasetaEvent):
        pass
