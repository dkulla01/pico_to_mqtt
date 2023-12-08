from __future__ import annotations

from datetime import timedelta
from pathlib import Path

import typed_settings as ts
from attr import Factory, field

from pico_to_mqtt.caseta.model import ButtonId

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
    username: str

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
    password: str


@ts.settings(frozen=True)
class DoubleClickWindow:
    power_on_double_click_window_ms: int = 300
    favorite_double_click_window_ms: int = 300
    power_off_double_click_window_ms: int = 300
    increase_double_click_window_ms: int = 750
    decrease_double_click_window_ms: int = 750

    def get_double_click_window(self, button_id: ButtonId) -> timedelta:
        match button_id:
            case ButtonId.POWER_ON:
                return timedelta(milliseconds=self.power_on_double_click_window_ms)
            case ButtonId.FAVORITE:
                return timedelta(milliseconds=self.favorite_double_click_window_ms)
            case ButtonId.POWER_OFF:
                return timedelta(milliseconds=self.power_off_double_click_window_ms)
            case ButtonId.INCREASE:
                return timedelta(milliseconds=self.increase_double_click_window_ms)
            case ButtonId.DECREASE:
                return timedelta(milliseconds=self.decrease_double_click_window_ms)

    @classmethod
    def default_instance(cls) -> DoubleClickWindow:
        return cls()


@ts.settings(frozen=True)
class ButtonWatcherConfig:
    double_click_window: DoubleClickWindow = field(
        default=Factory(DoubleClickWindow.default_instance)
    )
    sleep_duration_ms: int = 250
    max_duration_ms: int = 5000

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
    hostname: str
    port: int


def get_config() -> AllConfig:
    return ts.load(AllConfig, APP_NAME)
