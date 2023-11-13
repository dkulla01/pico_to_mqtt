from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timedelta
from typing import Optional

import attrs

from pico_to_mqtt.caseta.model import (
    ButtonAction,
    ButtonState,
    IllegalStateTransitionError,
)

LOGGER = logging.getLogger(__name__)


@attrs.define
class MutexLockedButtonState:
    mutex: asyncio.Lock
    state: ButtonState

    @classmethod
    def new_instance(cls) -> MutexLockedButtonState:
        return cls(asyncio.Lock(), ButtonState.NOT_PRESSED)


class ButtonHistory:
    def __init__(self, button_watcher_timeout: timedelta) -> None:
        self.mutex_locked_button_state = MutexLockedButtonState.new_instance()
        self._button_state: ButtonState = ButtonState.NOT_PRESSED
        self._tracking_started_at: Optional[datetime] = None
        self.is_finished: bool = False
        self._button_watcher_timeout = button_watcher_timeout

    async def increment(self, button_action: ButtonAction) -> None:
        async with self.mutex_locked_button_state.mutex:
            if not self.mutex_locked_button_state.state.is_button_action_valid(
                button_action
            ):
                raise IllegalStateTransitionError(
                    f"current button state is {self._button_state}, but received a "
                    f"button action of {button_action}"
                )
            if self.mutex_locked_button_state.state == ButtonState.NOT_PRESSED:
                self._tracking_started_at = datetime.now()
            self.mutex_locked_button_state.state = (
                self.mutex_locked_button_state.state.next_state()
            )

    @property
    def is_timed_out(self) -> bool:
        now = datetime.now()
        return (
            self._tracking_started_at is not None
            and (now - self._tracking_started_at) > self._button_watcher_timeout
        )


# class ButtonTracker:
#     def __init__(self, shutdown_condition: asyncio.Condition) -> None:
#         self._shutdown_condition = shutdown_condition
#         self._button_watchers_by_remote_id_lock = asyncio.Lock()
#         self._button_watchers_by_remote_id: Mapping[int, ButtonWatcher]
