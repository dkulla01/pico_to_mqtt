from __future__ import annotations

from pathlib import Path

import typed_settings as ts

from . import APP_NAME


@ts.settings
class AllConfig:
    caseta_config: CasetaConfig
    mqtt_config: MqttConfig


@ts.settings
class CasetaConfig:
    caseta_bridge_hostname: str
    path_to_caseta_client_cert: Path
    path_to_caseta_client_key: Path
    path_to_caseta_client_ca: Path


@ts.settings
class MqttConfig:
    path_to_mqtt_client_cert: Path
    path_to_mqtt_client_key: Path
    path_to_mqtt_client_ca: Path
    mqtt_hostname: str
    mqtt_port: int


def get_config() -> AllConfig:
    return ts.load(AllConfig, APP_NAME)
