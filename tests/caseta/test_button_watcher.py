from datetime import timedelta

import pytest
from pico_to_mqtt.caseta.button_watcher import ButtonHistory
from pico_to_mqtt.caseta.model import (
    ButtonAction,
    ButtonState,
    IllegalStateTransitionError,
)


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
async def test_button_history_increment_raises_exception_for_invalid_increment_actions():
    button_history = ButtonHistory(timedelta.max)
    async with button_history.mutex_locked_button_state.mutex:
        assert button_history.mutex_locked_button_state.state == ButtonState.NOT_PRESSED
    with pytest.raises(IllegalStateTransitionError):
        await button_history.increment(ButtonAction.RELEASE)


@pytest.mark.asyncio
async def test_button_history_reports_timeout_when_timeout_exceeded():
    negative_timedelta_timeout_window = timedelta(seconds=-1)
    button_history = ButtonHistory(negative_timedelta_timeout_window)
    await button_history.increment(ButtonAction.PRESS)
    assert button_history.is_timed_out
