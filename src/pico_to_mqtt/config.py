from __future__ import annotations

from datetime import timedelta
from pathlib import Path

import typed_settings as ts

from . import APP_NAME


@ts.settings(frozen=True)
class AllConfig:
    caseta_config: CasetaConfig
    mqtt_config: MqttConfig
    mqtt_credentials: MqttCredentials
    button_watcher_config: ButtonWatcherConfig


@ts.settings(frozen=True)
class CasetaConfig:
    caseta_bridge_hostname: str
    path_to_caseta_client_cert: Path
    path_to_caseta_client_key: Path
    path_to_caseta_client_ca: Path


@ts.settings(frozen=True)
class MqttCredentials:
    mqtt_username: str

    # note: for some reason, a ts.secret(converter=ts.Secret) converter
    # creates a ts.Secret[ts.Secret[str]]
    # this is why:
    # https://gitlab.com/sscherfke/typed-settings/-/blob/caed212cfdc4179299812b1932b1172739de6758/src/typed_settings/_core.py#L408 # noqa: E501
    # first, it uses the declared converters to create a Secret[str]
    # next, it sets settings_dict['path.to.key']
    # to the deserialized value (a Secret[str])
    # finally, it passes that dict back through the deserialization machinery
    # which calls ts.Secret's constructor on the Secret[str] value in the settings_dict
    # leading to a Secret[Secret[str]], which is not what we want.
    # so I'm going to file an issue, but I want to write this down while it's
    # fresh in my mind. and we'll use a plain ol' str for now
    mqtt_password: str


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
