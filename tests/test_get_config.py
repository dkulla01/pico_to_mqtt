import pytest
from typed_settings.exceptions import InvalidSettingsError
from pico_to_mqtt.config import get_config
from pico_to_mqtt.main import new_mqtt_client
from pytest_mock import MockerFixture

_REQUIRED_ENV = {
    "PICO_TO_MQTT_CASETA_CONFIG_CASETA_BRIDGE_HOSTNAME": "caseta.local",
    "PICO_TO_MQTT_CASETA_CONFIG_PATH_TO_CASETA_CLIENT_CERT": "/c/caseta.crt",
    "PICO_TO_MQTT_CASETA_CONFIG_PATH_TO_CASETA_CLIENT_KEY": "/c/caseta.key",
    "PICO_TO_MQTT_CASETA_CONFIG_PATH_TO_CASETA_CLIENT_CA": "/c/caseta-ca.crt",
    "PICO_TO_MQTT_MQTT_CONFIG_PATH_TO_MQTT_CLIENT_CERT": "/c/mqtt.crt",
    "PICO_TO_MQTT_MQTT_CONFIG_PATH_TO_MQTT_CLIENT_KEY": "/c/mqtt.key",
    "PICO_TO_MQTT_MQTT_CONFIG_PATH_TO_MQTT_CLIENT_CA": "/c/mqtt-ca.pem",
    "PICO_TO_MQTT_MQTT_CONFIG_HOSTNAME": "broker.local",
    "PICO_TO_MQTT_MQTT_CONFIG_PORT": "8883",
}

_CREDENTIAL_ENV = [
    "PICO_TO_MQTT_MQTT_CREDENTIALS_USERNAME",
    "PICO_TO_MQTT_MQTT_CREDENTIALS_PASSWORD",
]


@pytest.fixture(autouse=True)
def required_env(monkeypatch: pytest.MonkeyPatch):
    for name, value in _REQUIRED_ENV.items():
        monkeypatch.setenv(name, value)
    for name in _CREDENTIAL_ENV:
        monkeypatch.delenv(name, raising=False)


def _client_kwargs(mocker: MockerFixture):
    mock_client = mocker.patch("pico_to_mqtt.main.aiomqtt.Client")
    config = get_config()
    new_mqtt_client(config.mqtt_config, config.mqtt_credentials)
    _args, kwargs = mock_client.call_args
    return kwargs


def test_no_credentials_env_builds_client_without_username_or_password(
    mocker: MockerFixture,
):
    kwargs = _client_kwargs(mocker)

    assert kwargs["username"] is None
    assert kwargs["password"] is None


def test_credentials_env_builds_client_with_username_and_password(
    mocker: MockerFixture, monkeypatch: pytest.MonkeyPatch
):
    monkeypatch.setenv("PICO_TO_MQTT_MQTT_CREDENTIALS_USERNAME", "u")
    monkeypatch.setenv("PICO_TO_MQTT_MQTT_CREDENTIALS_PASSWORD", "p")

    kwargs = _client_kwargs(mocker)

    assert kwargs["username"] == "u"
    assert kwargs["password"] == "p"


@pytest.mark.parametrize("name", ["USERNAME", "PASSWORD"])
def test_only_one_credential_is_rejected(monkeypatch: pytest.MonkeyPatch, name: str):
    monkeypatch.setenv(f"PICO_TO_MQTT_MQTT_CREDENTIALS_{name}", "x")

    with pytest.raises(InvalidSettingsError, match="username and password"):
        get_config()


def test_empty_credentials_env_builds_client_without_username_or_password(
    mocker: MockerFixture, monkeypatch: pytest.MonkeyPatch
):
    monkeypatch.setenv("PICO_TO_MQTT_MQTT_CREDENTIALS_USERNAME", "")
    monkeypatch.setenv("PICO_TO_MQTT_MQTT_CREDENTIALS_PASSWORD", "")

    kwargs = _client_kwargs(mocker)

    assert kwargs["username"] is None
    assert kwargs["password"] is None


@pytest.mark.parametrize("empty", ["USERNAME", "PASSWORD"])
def test_empty_credential_with_a_real_one_is_rejected(
    monkeypatch: pytest.MonkeyPatch, empty: str
):
    other = "PASSWORD" if empty == "USERNAME" else "USERNAME"
    monkeypatch.setenv(f"PICO_TO_MQTT_MQTT_CREDENTIALS_{empty}", "")
    monkeypatch.setenv(f"PICO_TO_MQTT_MQTT_CREDENTIALS_{other}", "x")

    with pytest.raises(InvalidSettingsError, match="username and password"):
        get_config()
