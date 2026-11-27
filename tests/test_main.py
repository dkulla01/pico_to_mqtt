from pathlib import Path

from pico_to_mqtt.config import MqttConfig, MqttCredentials
from pico_to_mqtt.main import new_mqtt_client
from pytest_mock import MockerFixture

_MQTT_CONFIG = MqttConfig(
    path_to_mqtt_client_cert=Path("/certs/mqtt.crt"),
    path_to_mqtt_client_key=Path("/certs/mqtt.key"),
    path_to_mqtt_client_ca=Path("/certs/mqtt-ca.pem"),
    hostname="broker.local",
    port=8883,
)


def test_new_mqtt_client_without_credentials_passes_no_username_or_password(
    mocker: MockerFixture,
):
    mock_client = mocker.patch("pico_to_mqtt.main.aiomqtt.Client")

    new_mqtt_client(_MQTT_CONFIG, None)

    _args, kwargs = mock_client.call_args
    assert kwargs["username"] is None
    assert kwargs["password"] is None
    assert kwargs["tls_params"].certfile == "/certs/mqtt.crt"


def test_new_mqtt_client_with_credentials_passes_username_and_password(
    mocker: MockerFixture,
):
    mock_client = mocker.patch("pico_to_mqtt.main.aiomqtt.Client")

    new_mqtt_client(_MQTT_CONFIG, MqttCredentials(username="pico", password="pw"))

    _args, kwargs = mock_client.call_args
    assert kwargs["username"] == "pico"
    assert kwargs["password"] == "pw"
