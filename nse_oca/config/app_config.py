from __future__ import annotations

import configparser
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, List

from nse_oca.domain.models import OptionMode


ALLOWED_REFRESH_SECONDS = {60, 120, 180, 300, 600, 900}


class ConfigValidationError(ValueError):
    """Raised when supplied configuration cannot be validated."""


@dataclass(frozen=True)
class AppConfig:
    load_nse_icon: bool = True
    index: str = "NIFTY"
    stock: str = "360ONE"
    option_mode: OptionMode = OptionMode.INDEX
    seconds: int = 60
    live_export: bool = False
    save_oc: bool = False
    notifications: bool = False
    auto_stop: bool = False
    update: bool = True
    logging: bool = False
    warn_late_update: bool = False


def _first_or_default(values: Iterable[str], default: str) -> str:
    values_list = [value for value in values if value]
    return values_list[0] if values_list else default


def _validate_seconds(seconds: int) -> int:
    if seconds not in ALLOWED_REFRESH_SECONDS:
        return 60
    return seconds


def load_app_config(
    path: str | Path,
    available_indices: Iterable[str] = (),
    available_stocks: Iterable[str] = (),
) -> AppConfig:
    config_path = Path(path)

    parser = configparser.ConfigParser()
    parser.read(config_path)

    if not parser.has_section("main"):
        default_config = AppConfig(
            index=_first_or_default(available_indices, "NIFTY"),
            stock=_first_or_default(available_stocks, "360ONE"),
        )
        save_app_config(config_path, default_config)
        return default_config

    index_default = _first_or_default(available_indices, "NIFTY")
    stock_default = _first_or_default(available_stocks, "360ONE")

    index = parser.get("main", "index", fallback=index_default)
    stock = parser.get("main", "stock", fallback=stock_default)

    if available_indices and index not in set(available_indices):
        index = index_default
    if available_stocks and stock not in set(available_stocks):
        stock = stock_default

    option_mode_raw = parser.get("main", "option_mode", fallback=OptionMode.INDEX.value)
    option_mode = OptionMode(option_mode_raw) if option_mode_raw in OptionMode._value2member_map_ else OptionMode.INDEX

    seconds = _validate_seconds(parser.getint("main", "seconds", fallback=60))

    return AppConfig(
        load_nse_icon=parser.getboolean("main", "load_nse_icon", fallback=True),
        index=index,
        stock=stock,
        option_mode=option_mode,
        seconds=seconds,
        live_export=parser.getboolean("main", "live_export", fallback=False),
        save_oc=parser.getboolean("main", "save_oc", fallback=False),
        notifications=parser.getboolean("main", "notifications", fallback=False),
        auto_stop=parser.getboolean("main", "auto_stop", fallback=False),
        update=parser.getboolean("main", "update", fallback=True),
        logging=parser.getboolean("main", "logging", fallback=False),
        warn_late_update=parser.getboolean("main", "warn_late_update", fallback=False),
    )


def save_app_config(path: str | Path, config: AppConfig) -> None:
    config_path = Path(path)
    parser = configparser.ConfigParser()
    parser.add_section("main")

    parser.set("main", "load_nse_icon", str(config.load_nse_icon))
    parser.set("main", "index", config.index)
    parser.set("main", "stock", config.stock)
    parser.set("main", "option_mode", config.option_mode.value)
    parser.set("main", "seconds", str(_validate_seconds(config.seconds)))
    parser.set("main", "live_export", str(config.live_export))
    parser.set("main", "save_oc", str(config.save_oc))
    parser.set("main", "notifications", str(config.notifications))
    parser.set("main", "auto_stop", str(config.auto_stop))
    parser.set("main", "update", str(config.update))
    parser.set("main", "logging", str(config.logging))
    parser.set("main", "warn_late_update", str(config.warn_late_update))

    with config_path.open("w", encoding="utf-8") as config_file:
        parser.write(config_file)
