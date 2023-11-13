import asyncio
from asyncio import Condition
from typing import Any
from unittest.mock import AsyncMock, Mock

import pytest
from pico_to_mqtt.caseta.model import PicoThreeButtonRaiseLower
from pico_to_mqtt.caseta.topology import Topology
from pylutron_caseta.smartbridge import Smartbridge
from pytest_mock import MockerFixture

_SMARTBRIDGE_DEVICES = {
    "2": {
        "device_id": "2",
        "name": "test_remote",
        "type": PicoThreeButtonRaiseLower.TYPE,
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


@pytest.fixture
def mock_smartbridge(mocker: MockerFixture):
    mock_smartbridge = mocker.patch("pico_to_mqtt.caseta.topology.Smartbridge")
    mock_get_buttons = Mock(return_value=_SMARTBRIDGE_BUTTONS)
    mock_smartbridge.get_buttons = mock_get_buttons

    mock_get_devices = Mock(return_value=_SMARTBRIDGE_DEVICES)
    mock_smartbridge.get_devices = mock_get_devices

    mock_connect = AsyncMock()
    mock_smartbridge.connect = mock_connect

    return mock_smartbridge


@pytest.mark.asyncio
async def test_topology_connects_to_smartbridge(mock_smartbridge: Smartbridge):
    mock_connect = AsyncMock()
    mock_smartbridge.connect = mock_connect
    shutdown_condition = Condition()
    topology = Topology(mock_smartbridge, shutdown_condition)
    await topology.connect()
    mock_connect.assert_called_once()


@pytest.mark.asyncio
async def test_smartbridge_connection_errors_notify_the_shutdown_condition(
    mock_smartbridge: Smartbridge
):
    shutdown_condition = Condition()
    mock_connect_with_exception = AsyncMock(
        side_effect=Exception("Test that the topology responds to exceptions correctly")
    )
    mock_smartbridge.connect = mock_connect_with_exception
    topology = Topology(mock_smartbridge, shutdown_condition)

    # run the topology connection task -- which we know will have an exception thrown in it --
    # in a different task. We want to see that other task notify us in this task, where we'll
    # wait for the shutdown condition to be notified
    asyncio.create_task(topology.connect())

    # the shutdown_condition gets notified immediately, so waiting 500ms is quite generous
    async with asyncio.timeout(0.5):
        async with shutdown_condition:
            assert await shutdown_condition.wait()
            return
