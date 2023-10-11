from pico_to_mqtt.main import return_three_for_pytest_flow_check


def test_that_everything_is_packaged():
    assert return_three_for_pytest_flow_check() == 3
