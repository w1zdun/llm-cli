"""XDG config and data path resolution."""

import os
import stat
from pathlib import Path

_APP_NAME = "llm-cli"


def _xdg_config_home() -> Path:
    env = os.environ.get("XDG_CONFIG_HOME")
    if env:
        return Path(env)
    return Path.home() / ".config"


def _xdg_data_home() -> Path:
    env = os.environ.get("XDG_DATA_HOME")
    if env:
        return Path(env)
    return Path.home() / ".local" / "share"


def config_dir() -> Path:
    """Return the config directory (~/.config/llm-cli)."""
    return _xdg_config_home() / _APP_NAME


def config_path(name: str) -> Path:
    """Return a specific config file path (~/.config/llm-cli/<name>)."""
    return config_dir() / name


def data_dir() -> Path:
    """Return the data directory (~/.local/share/llm-cli)."""
    return _xdg_data_home() / _APP_NAME


def ensure_data_dir() -> Path:
    """Create the data directory with mode 0700 on first use."""
    d = data_dir()
    if not d.exists():
        d.mkdir(parents=True, mode=stat.S_IRWXU)
    return d


def runs_log_path() -> Path:
    """Return the runs.jsonl log file path."""
    return data_dir() / "runs.jsonl"
