import datetime
from datetime import timedelta
from typing import Callable
from unittest.mock import Mock

import pytest
from pico_to_mqtt.caseta.button_watcher import ButtonHistory
from pico_to_mqtt.caseta.model import (
    ButtonAction,
    ButtonState,
    IllegalStateTransitionError,
)


@pytest.mark.asyncio
async def test_increment_button_history_increments_through_all_button_states():
    button_history = ButtonHistory(timedelta.max, datetime.datetime.now)
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
    button_history = ButtonHistory(timedelta.max, datetime.datetime.now)
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
