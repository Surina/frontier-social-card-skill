#!/usr/bin/env python3
"""Local configuration and credential storage for the standalone skill."""

from __future__ import annotations

import getpass
import json
import os
from pathlib import Path

APP_NAME = "frontier-social-card-skill"
LEGACY_APP_NAME = "frontier-social-card"


def _config_dir(app_name: str) -> Path:
    override = os.environ.get("SOCIAL_IMAGE_POST_CONFIG_DIR")
    if override:
        return Path(override).expanduser()
    if os.name == "nt":
        root = Path(os.environ.get("APPDATA", Path.home()))
        return root / app_name
    root = Path(os.environ.get("XDG_CONFIG_HOME", Path.home() / ".config"))
    return root / app_name


def config_dir() -> Path:
    current = _config_dir(APP_NAME)
    legacy = _config_dir(LEGACY_APP_NAME)
    if not current.exists() and legacy.exists():
        return legacy
    return current


def config_path() -> Path:
    return config_dir() / "config.json"


def secret_path() -> Path:
    return config_dir() / ".credentials.json"


def load_config() -> dict:
    path = config_path()
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def save_config(value: dict) -> None:
    directory = config_dir()
    directory.mkdir(parents=True, exist_ok=True)
    path = config_path()
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2), encoding="utf-8")
    try:
        path.chmod(0o600)
    except OSError:
        pass


def _keyring():
    try:
        import keyring  # type: ignore
        return keyring
    except ImportError:
        return None


def save_secret(name: str, value: str) -> str:
    keyring = _keyring()
    if keyring is not None:
        try:
            keyring.set_password(APP_NAME, name, value)
            return "system_keyring"
        except Exception:
            pass
    directory = config_dir()
    directory.mkdir(parents=True, exist_ok=True)
    values = {}
    if secret_path().exists():
        values = json.loads(secret_path().read_text(encoding="utf-8"))
    values[name] = value
    secret_path().write_text(json.dumps(values), encoding="utf-8")
    try:
        secret_path().chmod(0o600)
    except OSError:
        pass
    return "private_file"


def load_secret(name: str) -> str:
    env_name = load_config().get("api_key_env")
    if env_name and os.environ.get(env_name):
        return os.environ[env_name]
    keyring = _keyring()
    if keyring is not None:
        try:
            for service_name in (APP_NAME, LEGACY_APP_NAME):
                value = keyring.get_password(service_name, name)
                if value:
                    return value
        except Exception:
            pass
    if secret_path().exists():
        return json.loads(secret_path().read_text(encoding="utf-8")).get(name, "")
    return ""


def delete_secret(name: str) -> None:
    keyring = _keyring()
    if keyring is not None:
        for service_name in (APP_NAME, LEGACY_APP_NAME):
            try:
                keyring.delete_password(service_name, name)
            except Exception:
                pass
    if secret_path().exists():
        values = json.loads(secret_path().read_text(encoding="utf-8"))
        values.pop(name, None)
        secret_path().write_text(json.dumps(values), encoding="utf-8")


def read_secret(prompt: str) -> str:
    return getpass.getpass(prompt).strip()
