import asyncio
import datetime
from unittest.mock import AsyncMock, Mock

import attr
import pytest
from pico_to_mqtt.caseta.button_watcher import ButtonWatcher
from pico_to_mqtt.caseta.model import (
    ButtonAction,
    ButtonId,
    PicoRemote,
    PicoRemoteType,
)
from pico_to_mqtt.config import ButtonWatcherConfig
from pico_to_mqtt.event_handler import ButtonEvent, CasetaEvent, EventHandler


@pytest.fixture
def january_first_midnight() -> datetime.datetime:
    return datetime.datetime.fromisoformat("2023-01-01T00:00:00Z")


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
def example_shutdown_condition():
    return asyncio.Condition()

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
    example_shutdown_condition: asyncio.Condition
) -> ButtonWatcher:
    return ButtonWatcher(
        example_pico_remote,
        example_button_id,
        example_button_watcher_config,
        example_event_handler,
        example_shutdown_condition,
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
