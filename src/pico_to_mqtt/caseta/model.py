from enum import Enum, StrEnum
from typing import Iterable, Mapping

import attrs


class IllegalStateTransitionError(Exception):
    """Raised when an out-of-order button state transition is requested"""

    pass


class ButtonId(Enum):
    """
    these button numbers are consistent for both Pico3ButtonRaiseLower and Pico2Button
    remotes
    """

    POWER_ON = 0
    FAVORITE = 1
    POWER_OFF = 2
    INCREASE = 3
    DECREASE = 4

    @classmethod
    def of_int(cls, value: int):
        return {member.value: member for member in cls}[value]

    @property
    def as_mqtt_topic_friendly_name(self):
        return self.name.lower().replace("_", "-")


class ButtonAction(Enum):
    PRESS = 0
    RELEASE = 1

    @classmethod
    def of_str(cls, value: str):
        return {member.name: member for member in cls}[value.upper()]


class ButtonState(Enum):
    NOT_PRESSED = 0
    FIRST_PRESS_AWAITING_RELEASE = 1
    FIRST_PRESS_AND_FIRST_RELEASE = 2
    SECOND_PRESS_AWAITING_RELEASE = 3
    DOUBLE_PRESS_FINISHED = 4

    def next_state(self):
        if self == ButtonState.DOUBLE_PRESS_FINISHED:
            raise IllegalStateTransitionError(
                "there is no state after finishing a double press"
            )
        return list(ButtonState)[self.value + 1]

    def is_button_action_valid(self, button_action: ButtonAction) -> bool:
        return (self.is_awaiting_press and button_action == ButtonAction.PRESS) or (
            self.is_awaiting_release and button_action == ButtonAction.RELEASE
        )

    @property
    def is_awaiting_press(self):
        return self in {
            ButtonState.NOT_PRESSED,
            ButtonState.FIRST_PRESS_AND_FIRST_RELEASE,
        }

    @property
    def is_awaiting_release(self):
        return self in {
            ButtonState.FIRST_PRESS_AWAITING_RELEASE,
            ButtonState.SECOND_PRESS_AWAITING_RELEASE,
        }


class PicoRemoteType(StrEnum):
    PICO_TWO_BUTTON = "Pico2Button"
    PICO_THREE_BUTTON_RAISE_LOWER = "Pico3ButtonRaiseLower"

    def as_str(self) -> str:
        return self.value

    @classmethod
    def from_str(cls, str_literal: str):
        match str_literal:
            case cls.PICO_THREE_BUTTON_RAISE_LOWER.value:
                return cls.PICO_THREE_BUTTON_RAISE_LOWER
            case cls.PICO_TWO_BUTTON.value:
                return cls.PICO_TWO_BUTTON
            case _:
                raise LookupError(
                    f"{str_literal} is not a valid, supported pico remote type"
                )

    @classmethod
    def values(cls) -> Iterable[str]:
        return {member.value for member in cls}


@attrs.frozen
class PicoRemote:
    device_id: int
    type: PicoRemoteType
    name: str
    area_name: str
    buttons_by_button_id: Mapping[int, ButtonId]
