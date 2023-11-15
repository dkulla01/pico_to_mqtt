from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timedelta
from typing import Callable, Optional

import attrs

from pico_to_mqtt.caseta.model import (
    ButtonAction,
    ButtonId,
    ButtonState,
    IllegalStateTransitionError,
    PicoRemote,
)
from pico_to_mqtt.config import ButtonWatcherConfig
from pico_to_mqtt.event_handler import ButtonEvent, CasetaEvent, EventHandler

LOGGER = logging.getLogger(__name__)


@attrs.mutable
class MutexLockedButtonState:
    mutex: asyncio.Lock
    state: ButtonState

    @classmethod
    def new_instance(cls) -> MutexLockedButtonState:
        return cls(asyncio.Lock(), ButtonState.NOT_PRESSED)


class ButtonHistory:
    def __init__(
        self,
        button_watcher_timeout: timedelta,
        current_time_provider: Callable[[], datetime] = datetime.now,
    ) -> None:
        self.mutex_locked_button_state = MutexLockedButtonState.new_instance()
        self._button_state: ButtonState = ButtonState.NOT_PRESSED
        self._tracking_started_at: Optional[datetime] = None
        self.is_finished: bool = False
        self._button_watcher_timeout = button_watcher_timeout
        self._current_time_provider = current_time_provider

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
                self._tracking_started_at = self._current_time_provider()
            self.mutex_locked_button_state.state = (
                self.mutex_locked_button_state.state.next_state()
            )

    def is_timed_out(self, now: datetime) -> bool:
        return (
            self._tracking_started_at is not None
            and (now - self._tracking_started_at) > self._button_watcher_timeout
        )


class ButtonWatcher:
    def __init__(
        self,
        pico_remote: PicoRemote,
        button_id: ButtonId,
        button_watcher_config: ButtonWatcherConfig,
        event_handler: EventHandler,
        current_instant_provider: Callable[[], datetime] = datetime.now,
    ) -> None:
        self._pico_remote = pico_remote
        self._button_id = button_id
        self._button_watcher_config = button_watcher_config
        self._event_handler = event_handler
        self._current_instant_provider = current_instant_provider
        self._button_history = ButtonHistory(
            button_watcher_config.max_duration,
            current_time_provider=current_instant_provider,
        )

    @property
    def button_log_prefix(self) -> str:
        return (
            f"remote: <id: {self._pico_remote.device_id}, "
            f"type: {self._pico_remote.type}, "
            f"name: {self._pico_remote.name}>, "
            f"button:{self._button_id}"
        )

    async def button_watcher_loop(self) -> None:
        button_history = self._button_history

        button_tracking_window_end = (
            self._current_instant_provider() + self._button_watcher_config.max_duration
        )

        await asyncio.sleep(
            self._button_watcher_config.double_click_window.total_seconds()
        )

        await self._handle_initial_tracking_checkpoint()
        if button_history.is_finished:
            return

        while self._current_instant_provider() < button_tracking_window_end:
            await asyncio.sleep(
                self._button_watcher_config.sleep_duration.total_seconds()
            )

            await self._handle_remaining_tracking_checkpoints()
            if button_history.is_finished:
                return
        button_history.is_finished = True
        LOGGER.debug(
            (
                "%s: the button tracking window ended without the button "
                "reaching a terminal state"
            ),
            self.button_log_prefix,
        )

    async def _handle_initial_tracking_checkpoint(self):
        button_history = self._button_history
        async with button_history.mutex_locked_button_state.mutex:
            current_state = button_history.mutex_locked_button_state.state
            if current_state == ButtonState.FIRST_PRESS_AND_FIRST_RELEASE:
                LOGGER.debug("%s a single press has completed", self.button_log_prefix)
                button_history.is_finished = True
                await self._event_handler.handle_event(
                    CasetaEvent(
                        self._pico_remote,
                        self._button_id,
                        ButtonEvent.SINGLE_PRESS_COMPLETED,
                    )
                )
                return
            elif current_state == ButtonState.DOUBLE_PRESS_FINISHED:
                LOGGER.debug("%s: A double press has completed", self.button_log_prefix)
                button_history.is_finished = True
                await self._event_handler.handle_event(
                    CasetaEvent(
                        self._pico_remote,
                        self._button_id,
                        ButtonEvent.DOUBLE_PRESS_COMPLETED,
                    )
                )
                return
            elif current_state == ButtonState.FIRST_PRESS_AWAITING_RELEASE:
                LOGGER.debug(
                    "%s: A long press has started but not completed",
                    self.button_log_prefix,
                )
                await self._event_handler.handle_event(
                    CasetaEvent(
                        self._pico_remote,
                        self._button_id,
                        ButtonEvent.LONG_PRESS_ONGOING,
                    )
                )
            else:
                LOGGER.debug(
                    "%s: current button state is %s",
                    self.button_log_prefix,
                    current_state,
                )

    async def _handle_remaining_tracking_checkpoints(self):
        async with self._button_history.mutex_locked_button_state.mutex:
            current_state = self._button_history.mutex_locked_button_state.state
            if current_state == ButtonState.FIRST_PRESS_AND_FIRST_RELEASE:
                LOGGER.debug("%s a long press has completed", self.button_log_prefix)
                self._button_history.is_finished = True
                return
            elif current_state == ButtonState.DOUBLE_PRESS_FINISHED:
                LOGGER.debug("%s: A double press has completed", self.button_log_prefix)
                self._button_history.is_finished = True
                return
            elif current_state == ButtonState.FIRST_PRESS_AWAITING_RELEASE:
                LOGGER.debug(
                    "%s: A long press is still ongoing",
                    self.button_log_prefix,
                )
            else:
                LOGGER.debug(
                    "%s: current button state is %s",
                    self.button_log_prefix,
                    current_state,
                )

    async def increment_history(self, button_action: ButtonAction):
        await self._button_history.increment(button_action)


# class ButtonTracker:
#     def __init__(self, shutdown_condition: asyncio.Condition) -> None:
#         self._shutdown_condition = shutdown_condition
#         self._button_watchers_by_remote_id_lock = asyncio.Lock()
#         self._button_watchers_by_remote_id: Mapping[int, ButtonWatcher]
