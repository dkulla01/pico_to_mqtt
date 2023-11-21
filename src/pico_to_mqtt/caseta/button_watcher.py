from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timedelta
from typing import Any, Callable, MutableMapping, Optional

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
        current_time_provider: Callable[[], datetime],
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
        shutdown_condition: asyncio.Condition,
        current_instant_provider: Callable[[], datetime],
    ) -> None:
        self._pico_remote = pico_remote
        self._button_id = button_id
        self._button_watcher_config = button_watcher_config
        self._event_handler = event_handler
        self._current_instant_provider = current_instant_provider
        self._shutdown_condition = shutdown_condition
        self.button_history = ButtonHistory(
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
        try:
            button_history = self.button_history

            button_tracking_window_end = (
                self._current_instant_provider()
                + self._button_watcher_config.max_duration
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

                await self._handle_followup_tracking_checkpoints()
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
        except Exception as e:
            LOGGER.error(
                "%s: encountered a problem watching this button",
                self.button_log_prefix,
                e,
            )
            async with self._shutdown_condition:
                self._shutdown_condition.notify()
            raise e

    async def _handle_initial_tracking_checkpoint(self):
        button_history = self.button_history
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

    async def _handle_followup_tracking_checkpoints(self):
        async with self.button_history.mutex_locked_button_state.mutex:
            current_state = self.button_history.mutex_locked_button_state.state
            if current_state == ButtonState.FIRST_PRESS_AND_FIRST_RELEASE:
                LOGGER.debug("%s a long press has completed", self.button_log_prefix)
                self.button_history.is_finished = True
                await self._event_handler.handle_event(
                    CasetaEvent(
                        self._pico_remote,
                        self._button_id,
                        ButtonEvent.LONG_PRESS_COMPLETED,
                    )
                )
                return
            elif current_state == ButtonState.DOUBLE_PRESS_FINISHED:
                LOGGER.debug("%s: A double press has completed", self.button_log_prefix)
                self.button_history.is_finished = True
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
                    "%s: A long press is still ongoing",
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

    async def increment_history(self, button_action: ButtonAction):
        await self.button_history.increment(button_action)


@attrs.frozen(kw_only=True)
class MutexLockedButtonTrackers:
    mutex: asyncio.Lock
    button_watchers_by_remote_id: MutableMapping[int, ButtonWatcher]


class ButtonTracker:
    def __init__(
        self,
        shutdown_condition: asyncio.Condition,
        caseta_event_handler: EventHandler,
        button_watcher_config: ButtonWatcherConfig,
        current_instant_provider: Callable[[], datetime] = datetime.now,
    ) -> None:
        self._shutdown_condition = shutdown_condition
        self._caseta_event_handler = caseta_event_handler
        self._button_watcher_config = button_watcher_config
        self._mutex_locked_button_watchers = MutexLockedButtonTrackers(
            mutex=asyncio.Lock(), button_watchers_by_remote_id=dict()
        )
        self._current_instant_provider = current_instant_provider

    def button_event_callback(
        self, remote: PicoRemote, button_id: ButtonId
    ) -> Callable[[str], Any]:
        return lambda button_event_str: asyncio.get_running_loop().create_task(
            self._process_button_event(
                remote, button_id, ButtonAction.of_str(button_event_str)
            )
        )

    async def _process_button_event(
        self, remote: PicoRemote, button_id: ButtonId, button_action: ButtonAction
    ):
        """visible for testing"""
        remote_info_logging_str = (
            f"remote: (name: {remote.name}, "
            "id: {remote.device_id}, button_id: {button_id})"
        )
        LOGGER.info(
            "got a button event: %s, button_action: %s",
            remote_info_logging_str,
            button_action,
        )

        async with self._mutex_locked_button_watchers.mutex:
            button_watcher: Optional[
                ButtonWatcher
            ] = self._mutex_locked_button_watchers.button_watchers_by_remote_id.get(
                remote.device_id
            )
            if (
                not button_watcher
                or not button_watcher.button_history
                or button_watcher.button_history.is_finished
                or button_watcher.button_history.is_timed_out(
                    self._current_instant_provider()
                )
            ):
                if button_action == ButtonAction.RELEASE:
                    LOGGER.debug(
                        (
                            "button event: %s, ButtonAction: %s, "
                            "button action does not correspond to a "
                            "button currently being tracked. ignoring it"
                        ),
                        remote_info_logging_str,
                        button_action,
                    )
                    return
                button_watcher = ButtonWatcher(
                    remote,
                    button_id,
                    self._button_watcher_config,
                    self._caseta_event_handler,
                    self._shutdown_condition,
                    self._current_instant_provider,
                )
                await button_watcher.increment_history(button_action)
                asyncio.create_task(button_watcher.button_watcher_loop())
            else:
                await button_watcher.increment_history(button_action)
            self._mutex_locked_button_watchers.button_watchers_by_remote_id[
                remote.device_id
            ] = button_watcher
