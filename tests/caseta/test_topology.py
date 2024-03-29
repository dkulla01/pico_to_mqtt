import asyncio
from asyncio import Condition
from unittest.mock import AsyncMock, Mock

import pytest
from pico_to_mqtt.caseta.button_watcher import ButtonTracker
from pico_to_mqtt.caseta.model import PicoRemoteType
from pico_to_mqtt.caseta.topology import Topology
from pylutron_caseta.smartbridge import Smartbridge
from pytest_mock import MockerFixture

_AREA_ID = "99"
_AREA_NAME = "fancyroom"
_REMOTE_NAME = "entrywayremote"
_SMARTBRIDGE_DEVICES = {
    "2": {
        "device_id": "2",
        "name": f"{_AREA_NAME}_{_REMOTE_NAME}",
        "area": _AREA_ID,
        "type": PicoRemoteType.PICO_THREE_BUTTON_RAISE_LOWER.value,
    },
    "1": {"device_id": "1", "name": "Smart Bridge", "type": "SmartBridge"},
}


_SMARTBRIDGE_BUTTONS = {
    "100": {"device_id": "100", "button_number": 0, "parent_device": "2"},
    "101": {"device_id": "101", "button_number": 1, "parent_device": "2"},
    "102": {"device_id": "102", "button_number": 2, "parent_device": "2"},
    "103": {"device_id": "103", "button_number": 3, "parent_device": "2"},
    "104": {"device_id": "104", "button_number": 4, "parent_device": "2"},
}

_SMARTBRIDGE_AREAS = {"99": {"id": "99", "name": _AREA_NAME}}


@pytest.fixture
def mock_smartbridge(mocker: MockerFixture):
    mock_smartbridge = mocker.patch("pico_to_mqtt.caseta.topology.Smartbridge")
    mock_get_buttons = Mock(return_value=_SMARTBRIDGE_BUTTONS)
    mock_smartbridge.get_buttons = mock_get_buttons

    mock_get_devices = Mock(return_value=_SMARTBRIDGE_DEVICES)
    mock_smartbridge.get_devices = mock_get_devices

    setattr(mock_smartbridge, "areas", _SMARTBRIDGE_AREAS)

    mock_connect = AsyncMock()
    mock_smartbridge.connect = mock_connect

    return mock_smartbridge


@pytest.fixture
def mock_button_tracker(mocker: MockerFixture):
    button_tracker = mocker.patch("pico_to_mqtt.caseta.topology.ButtonTracker")
    button_tracker.button_event_callback = mocker.Mock()
    return button_tracker


@pytest.mark.asyncio
async def test_topology_connects_to_smartbridge(
    mock_smartbridge: Smartbridge, mock_button_tracker: ButtonTracker
):
    mock_connect = AsyncMock()
    mock_smartbridge.connect = mock_connect
    shutdown_condition = Condition()
    topology = Topology(mock_smartbridge, shutdown_condition, mock_button_tracker)
    await topology.connect()
    mock_connect.assert_called_once()


@pytest.mark.asyncio
async def test_smartbridge_connection_errors_notify_the_shutdown_condition(
    mock_smartbridge: Smartbridge, mock_button_tracker: ButtonTracker
):
    shutdown_condition = Condition()
    mock_connect_with_exception = AsyncMock(
        side_effect=Exception("Test that the topology responds to exceptions correctly")
    )
    mock_smartbridge.connect = mock_connect_with_exception
    topology = Topology(mock_smartbridge, shutdown_condition, mock_button_tracker)

    # run the topology connection task -- which we know will have an exception thrown
    # in it -- in a different task. We want to see that other task notify us in this
    # task, where we'll wait for the shutdown condition to be notified
    asyncio.create_task(topology.connect())

    # the shutdown_condition gets notified immediately, so waiting 500ms is
    # quite generous
    async with asyncio.timeout(0.5):
        async with shutdown_condition:
            assert await shutdown_condition.wait()
            return
