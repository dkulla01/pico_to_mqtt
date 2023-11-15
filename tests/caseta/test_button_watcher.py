import datetime
from datetime import timedelta
from typing import Callable
from unittest.mock import AsyncMock, Mock

import attr
import pytest
from pico_to_mqtt.caseta.button_watcher import ButtonHistory, ButtonWatcher
from pico_to_mqtt.caseta.model import (
    ButtonAction,
    ButtonId,
    ButtonState,
    IllegalStateTransitionError,
    PicoRemote,
    PicoRemoteType,
)
from pico_to_mqtt.config import ButtonWatcherConfig
from pico_to_mqtt.event_handler import ButtonEvent, CasetaEvent, EventHandler


@pytest.mark.asyncio
async def test_increment_button_history_increments_through_all_button_states():
    button_history = ButtonHistory(timedelta.max)
    async with button_history.mutex_locked_button_state.mutex:
        assert button_history.mutex_locked_button_state.state == ButtonState.NOT_PRESSED
    await button_history.increment(ButtonAction.PRESS)
    async with button_history.mutex_locked_button_state.mutex:
        assert (
            button_history.mutex_locked_button_state.state
            == ButtonState.FIRST_PRESS_AWAITING_RELEASE
        )

    await button_history.increment(ButtonAction.RELEASE)
    async with button_history.mutex_locked_button_state.mutex:
        assert (
            button_history.mutex_locked_button_state.state
            == ButtonState.FIRST_PRESS_AND_FIRST_RELEASE
        )

    await button_history.increment(ButtonAction.PRESS)
    async with button_history.mutex_locked_button_state.mutex:
        assert (
            button_history.mutex_locked_button_state.state
            == ButtonState.SECOND_PRESS_AWAITING_RELEASE
        )

    await button_history.increment(ButtonAction.RELEASE)
    async with button_history.mutex_locked_button_state.mutex:
        assert (
            button_history.mutex_locked_button_state.state
            == ButtonState.DOUBLE_PRESS_FINISHED
        )


@pytest.mark.asyncio
async def test_button_history_increment_raises_exception_for_invalid_increments():
    button_history = ButtonHistory(timedelta.max)
    async with button_history.mutex_locked_button_state.mutex:
        assert button_history.mutex_locked_button_state.state == ButtonState.NOT_PRESSED
    with pytest.raises(IllegalStateTransitionError):
        await button_history.increment(ButtonAction.RELEASE)


@pytest.fixture
def january_first_midnight() -> datetime.datetime:
    return datetime.datetime.fromisoformat("2023-01-01T00:00:00Z")


@pytest.mark.asyncio
async def test_button_history_reports_timeout_when_timeout_exceeded(
    january_first_midnight: datetime.datetime
):
    timeout = timedelta(seconds=1)
    longer_than_timeout = timeout * 2

    now_provider: Callable[[], datetime.datetime] = Mock(
        return_value=january_first_midnight
    )
    button_history = ButtonHistory(timeout, now_provider)
    await button_history.increment(ButtonAction.PRESS)
    assert button_history.is_timed_out(january_first_midnight + longer_than_timeout)


@pytest.fixture
def example_pico_remote() -> PicoRemote:
    buttons_by_button_id = {
        1: ButtonId.POWER_ON,
        2: ButtonId.POWER_OFF,
        3: ButtonId.INCREASE,
        4: ButtonId.DECREASE,
        5: ButtonId.FAVORITE,
    }
    return PicoRemote(
        99,
        PicoRemoteType.PICO_THREE_BUTTON_RAISE_LOWER,
        "some_test_remote",
        buttons_by_button_id,
    )


@pytest.fixture
def example_button_watcher_config():
    return ButtonWatcherConfig()


@pytest.fixture
def example_button_id():
    return ButtonId.POWER_ON


@pytest.fixture
def mock_handle_event_method():
    return AsyncMock()


@pytest.fixture
def example_event_handler(mock_handle_event_method: AsyncMock):
    event_handler = Mock(EventHandler)
    event_handler.handle_event = mock_handle_event_method
    return event_handler


@pytest.fixture
def example_button_watcher(
    january_first_midnight: datetime.datetime,
    example_pico_remote: PicoRemote,
    example_button_watcher_config: ButtonWatcherConfig,
    example_button_id: ButtonId,
    example_event_handler: EventHandler,
) -> ButtonWatcher:
    return ButtonWatcher(
        example_pico_remote,
        example_button_id,
        example_button_watcher_config,
        example_event_handler,
        lambda: january_first_midnight,
    )


@pytest.fixture
def expected_caseta_event_scaffold(
    example_pico_remote: PicoRemote, example_button_id: ButtonId
) -> CasetaEvent:
    return CasetaEvent(
        example_pico_remote, example_button_id, ButtonEvent.SINGLE_PRESS_COMPLETED
    )


@pytest.mark.asyncio
async def test_initial_button_watcher_checkpoint_sees_long_press_started(
    example_button_watcher: ButtonWatcher,
    expected_caseta_event_scaffold: CasetaEvent,
    mock_handle_event_method: AsyncMock,
):
    await example_button_watcher.increment_history(ButtonAction.PRESS)
    await example_button_watcher._handle_initial_tracking_checkpoint()  # pyright: ignore[reportPrivateUsage]
    expected_event = attr.evolve(
        expected_caseta_event_scaffold, button_event=ButtonEvent.LONG_PRESS_ONGOING
    )

    mock_handle_event_method.assert_awaited_with(expected_event)


@pytest.mark.asyncio
async def test_initial_button_watcher_checkpoint_sees_single_click(
    example_button_watcher: ButtonWatcher,
    expected_caseta_event_scaffold: CasetaEvent,
    mock_handle_event_method: AsyncMock,
):
    await example_button_watcher.increment_history(ButtonAction.PRESS)
    await example_button_watcher.increment_history(ButtonAction.RELEASE)

    await example_button_watcher._handle_initial_tracking_checkpoint()  # pyright: ignore[reportPrivateUsage]
    expected_event = attr.evolve(
        expected_caseta_event_scaffold, button_event=ButtonEvent.SINGLE_PRESS_COMPLETED
    )
    mock_handle_event_method.assert_awaited_with(expected_event)


@pytest.mark.asyncio
async def test_initial_checkpoint_does_not_emit_event_for_incomplete_double_click(
    example_button_watcher: ButtonWatcher,
    mock_handle_event_method: AsyncMock,
):
    # this is the first, complete click of a long double click
    await example_button_watcher.increment_history(ButtonAction.PRESS)
    await example_button_watcher.increment_history(ButtonAction.RELEASE)

    # this is the second, incomplete click of a long double click.
    # the button has been pressed a second time, but not yet released.
    await example_button_watcher.increment_history(ButtonAction.PRESS)

    await example_button_watcher._handle_initial_tracking_checkpoint()  # pyright: ignore[reportPrivateUsage]
    mock_handle_event_method.assert_not_awaited()


@pytest.mark.asyncio
async def test_initial_checkpoint_sees_double_click(
    example_button_watcher: ButtonWatcher,
    expected_caseta_event_scaffold: CasetaEvent,
    mock_handle_event_method: AsyncMock,
):
    # this is the first, complete click of a double click
    await example_button_watcher.increment_history(ButtonAction.PRESS)
    await example_button_watcher.increment_history(ButtonAction.RELEASE)

    # this is the second, complete click of a double click
    await example_button_watcher.increment_history(ButtonAction.PRESS)
    await example_button_watcher.increment_history(ButtonAction.RELEASE)

    await example_button_watcher._handle_initial_tracking_checkpoint()  # pyright: ignore[reportPrivateUsage]
    expected_event = attr.evolve(
        expected_caseta_event_scaffold, button_event=ButtonEvent.DOUBLE_PRESS_COMPLETED
    )
    mock_handle_event_method.assert_awaited_with(expected_event)


@pytest.mark.asyncio
async def test_followup_checkpoint_sees_long_press_ongoing(
    example_button_watcher: ButtonWatcher,
    expected_caseta_event_scaffold: CasetaEvent,
    mock_handle_event_method: AsyncMock,
):
    await example_button_watcher.increment_history(ButtonAction.PRESS)
    await example_button_watcher._handle_followup_tracking_checkpoints()  # pyright: ignore[reportPrivateUsage]
    expected_event = attr.evolve(
        expected_caseta_event_scaffold, button_event=ButtonEvent.LONG_PRESS_ONGOING
    )

    mock_handle_event_method.assert_awaited_with(expected_event)


@pytest.mark.asyncio
async def test_followup_checkpoint_sees_long_press_completed(
    example_button_watcher: ButtonWatcher,
    expected_caseta_event_scaffold: CasetaEvent,
    mock_handle_event_method: AsyncMock,
):
    await example_button_watcher.increment_history(ButtonAction.PRESS)
    await example_button_watcher.increment_history(ButtonAction.RELEASE)
    await example_button_watcher._handle_followup_tracking_checkpoints()  # pyright: ignore[reportPrivateUsage]
    expected_event = attr.evolve(
        expected_caseta_event_scaffold, button_event=ButtonEvent.LONG_PRESS_COMPLETED
    )

    mock_handle_event_method.assert_awaited_with(expected_event)


@pytest.mark.asyncio
async def test_followup_checkpoint_emits_no_event_for_ongoing_double_press(
    example_button_watcher: ButtonWatcher,
    mock_handle_event_method: AsyncMock,
):
    # this is the first, complete click of a double click
    await example_button_watcher.increment_history(ButtonAction.PRESS)
    await example_button_watcher.increment_history(ButtonAction.RELEASE)

    # this is the second, incomplete click of a double click
    # the button has been pressed a second time, but not released
    await example_button_watcher.increment_history(ButtonAction.PRESS)

    await example_button_watcher._handle_followup_tracking_checkpoints()  # pyright: ignore[reportPrivateUsage]
    mock_handle_event_method.assert_not_awaited()


@pytest.mark.asyncio
async def test_followup_checkpoint_sees_double_press_completed(
    example_button_watcher: ButtonWatcher,
    expected_caseta_event_scaffold: CasetaEvent,
    mock_handle_event_method: AsyncMock,
):
    # this is the first, complete click of a double click
    await example_button_watcher.increment_history(ButtonAction.PRESS)
    await example_button_watcher.increment_history(ButtonAction.RELEASE)

    # this is the second, complete click of a double click
    await example_button_watcher.increment_history(ButtonAction.PRESS)
    await example_button_watcher.increment_history(ButtonAction.RELEASE)

    await example_button_watcher._handle_followup_tracking_checkpoints()  # pyright: ignore[reportPrivateUsage]
    expected_event = attr.evolve(
        expected_caseta_event_scaffold, button_event=ButtonEvent.DOUBLE_PRESS_COMPLETED
    )

    mock_handle_event_method.assert_awaited_with(expected_event)
