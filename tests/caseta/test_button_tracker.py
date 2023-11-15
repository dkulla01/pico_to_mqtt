import asyncio
import datetime
from unittest.mock import Mock

import pytest
from pico_to_mqtt.caseta.button_watcher import ButtonTracker
from pico_to_mqtt.caseta.model import ButtonAction, ButtonId, PicoRemote, PicoRemoteType
from pico_to_mqtt.config import ButtonWatcherConfig
from pico_to_mqtt.event_handler import EventHandler
from pytest_mock import MockerFixture


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
def mock_event_handler(mocker: MockerFixture):
    return mocker.Mock(EventHandler)


@pytest.fixture
def mock_shutdown_condition(mocker: MockerFixture):
    return mocker.Mock(asyncio.Condition)


@pytest.fixture
def mock_asyncio_create_task(mocker: MockerFixture):
    return mocker.patch("pico_to_mqtt.caseta.button_watcher.asyncio.create_task")


@pytest.mark.asyncio
async def test_button_tracker_tracks_a_new_button_press_event(
    mock_shutdown_condition: asyncio.Condition,
    example_pico_remote: PicoRemote,
    example_button_id: ButtonId,
    mock_event_handler: EventHandler,
    example_button_watcher_config: ButtonWatcherConfig,
    january_first_midnight: datetime.datetime,
    mock_asyncio_create_task: Mock
):
    button_tracker = ButtonTracker(
        mock_shutdown_condition,
        mock_event_handler,
        example_button_watcher_config,
        lambda: january_first_midnight,
    )

    await button_tracker._process_button_event(  # pyright: ignore[reportPrivateUsage]
        example_pico_remote, example_button_id, ButtonAction.PRESS
    )

    mock_asyncio_create_task.assert_called()

@pytest.mark.asyncio
async def test_button_tracker_does_not_track_an_initial_release_event(
    mock_shutdown_condition: asyncio.Condition,
    example_pico_remote: PicoRemote,
    example_button_id: ButtonId,
    mock_event_handler: EventHandler,
    example_button_watcher_config: ButtonWatcherConfig,
    january_first_midnight: datetime.datetime,
    mock_asyncio_create_task: Mock
):
    button_tracker = ButtonTracker(
        mock_shutdown_condition,
        mock_event_handler,
        example_button_watcher_config,
        lambda: january_first_midnight,
    )

    await button_tracker._process_button_event(  # pyright: ignore[reportPrivateUsage]
        example_pico_remote, example_button_id, ButtonAction.RELEASE
    )

    mock_asyncio_create_task.assert_not_called()

@pytest.mark.asyncio
async def test_button_tracker_increments_an_existing_button_watcher(
    mock_shutdown_condition: asyncio.Condition,
    example_pico_remote: PicoRemote,
    example_button_id: ButtonId,
    mock_event_handler: EventHandler,
    example_button_watcher_config: ButtonWatcherConfig,
    january_first_midnight: datetime.datetime,
    mock_asyncio_create_task: Mock
):
    button_tracker = ButtonTracker(
        mock_shutdown_condition,
        mock_event_handler,
        example_button_watcher_config,
        lambda: january_first_midnight,
    )

    await button_tracker._process_button_event(  # pyright: ignore[reportPrivateUsage]
        example_pico_remote, example_button_id, ButtonAction.PRESS
    )

    mock_asyncio_create_task.assert_called()
    mock_asyncio_create_task.reset_mock()
    await button_tracker._process_button_event(  # pyright: ignore[reportPrivateUsage]
        example_pico_remote, example_button_id, ButtonAction.RELEASE
    )
    mock_asyncio_create_task.assert_not_called()
