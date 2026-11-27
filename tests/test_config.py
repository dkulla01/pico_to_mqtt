from pathlib import Path

import typed_settings as ts
from pico_to_mqtt.config import AllConfig, MqttCredentials

_BASE_SETTINGS = """
[pico-to-mqtt.caseta-config]
caseta_bridge_hostname = "caseta-bridge.local"
path_to_caseta_client_cert = "/certs/caseta.crt"
path_to_caseta_client_key = "/certs/caseta.key"
path_to_caseta_client_ca = "/certs/caseta-ca.crt"

[pico-to-mqtt.mqtt-config]
path_to_mqtt_client_cert = "/certs/mqtt.crt"
path_to_mqtt_client_key = "/certs/mqtt.key"
path_to_mqtt_client_ca = "/certs/mqtt-ca.pem"
hostname = "broker.local"
port = 8883

[pico-to-mqtt.button-watcher-config]
"""

_CREDENTIALS_SETTINGS = """
[pico-to-mqtt.mqtt-credentials]
username = "pico"
password = "hunter2"
"""


def _load(tmp_path: Path, contents: str) -> AllConfig:
    settings_file = tmp_path / "settings.toml"
    settings_file.write_text(contents)
    return ts.load(AllConfig, "pico-to-mqtt", config_files=[settings_file])


def test_config_without_mqtt_credentials_loads_with_empty_credentials(tmp_path: Path):
    config = _load(tmp_path, _BASE_SETTINGS)

    assert config.mqtt_credentials == MqttCredentials()


def test_config_with_mqtt_credentials_loads_them(tmp_path: Path):
    config = _load(tmp_path, _BASE_SETTINGS + _CREDENTIALS_SETTINGS)

    assert config.mqtt_credentials == MqttCredentials(
        username="pico", password="hunter2"
    )
