from __future__ import annotations

from datetime import timedelta
from pathlib import Path

import typed_settings as ts

from . import APP_NAME


@ts.settings
class AllConfig:
    caseta_config: CasetaConfig
    mqtt_config: MqttConfig
    button_watcher_config: ButtonWatcherConfig


@ts.settings(frozen=True)
class CasetaConfig:
    caseta_bridge_hostname: str
    path_to_caseta_client_cert: Path
    path_to_caseta_client_key: Path
    path_to_caseta_client_ca: Path


@ts.settings(frozen=True)
class ButtonWatcherConfig:
    double_click_window_ms: int = 500
    sleep_duration_ms: int = 250
    max_duration_ms: int = 5000

    @property
    def double_click_window(self) -> timedelta:
        return timedelta(milliseconds=self.double_click_window_ms)

    @property
    def sleep_duration(self) -> timedelta:
        return timedelta(milliseconds=self.sleep_duration_ms)

    @property
    def max_duration(self) -> timedelta:
        return timedelta(milliseconds=self.max_duration_ms)


@ts.settings(frozen=True)
class MqttConfig:
    path_to_mqtt_client_cert: Path
    path_to_mqtt_client_key: Path
    path_to_mqtt_client_ca: Path
    mqtt_hostname: str
    mqtt_port: int


def get_config() -> AllConfig:
    return ts.load(AllConfig, APP_NAME)
