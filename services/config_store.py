"""Thread-safe, crash-safe storage for vision_config.json."""

import json
import os
import stat
import tempfile
from pathlib import Path
from threading import RLock


CONFIG_FILE = Path(
    os.getenv("VISION_CONFIG_PATH", Path(__file__).resolve().parent.parent / "vision_config.json")
)
_config_lock = RLock()


class ConfigStoreError(RuntimeError):
    """Base error for vision configuration persistence."""


class ConfigReadError(ConfigStoreError):
    """Raised when the current configuration cannot be read safely."""


class ConfigWriteError(ConfigStoreError):
    """Raised when a replacement configuration cannot be persisted safely."""


def read_config():
    with _config_lock:
        try:
            with CONFIG_FILE.open("r", encoding="utf-8") as config_file:
                config = json.load(config_file)
        except (OSError, UnicodeError, json.JSONDecodeError) as exc:
            raise ConfigReadError(
                "No se pudo leer la configuracion de vision en {0}: {1}".format(
                    CONFIG_FILE, exc
                )
            ) from exc
        if not isinstance(config, dict):
            raise ConfigReadError(
                "La configuracion de vision en {0} debe ser un objeto JSON".format(
                    CONFIG_FILE
                )
            )
        return config


def write_config(config):
    """Atomically replace the config file after forcing its bytes to storage."""
    with _config_lock:
        if not isinstance(config, dict):
            raise ConfigWriteError("La configuracion de vision debe ser un objeto JSON")
        CONFIG_FILE.parent.mkdir(parents=True, exist_ok=True)
        temp_path = None
        try:
            file_mode = (
                stat.S_IMODE(CONFIG_FILE.stat().st_mode)
                if CONFIG_FILE.exists()
                else 0o644
            )
            descriptor, temp_path = tempfile.mkstemp(
                prefix=".{0}.".format(CONFIG_FILE.name),
                suffix=".tmp",
                dir=CONFIG_FILE.parent,
            )
            os.fchmod(descriptor, file_mode)
            with os.fdopen(descriptor, "w", encoding="utf-8") as config_file:
                json.dump(config, config_file, indent=2)
                config_file.write("\n")
                config_file.flush()
                os.fsync(config_file.fileno())
            os.replace(temp_path, CONFIG_FILE)
            temp_path = None

            # Persist the rename itself on Linux/Raspberry Pi filesystems.
            directory_fd = os.open(CONFIG_FILE.parent, os.O_DIRECTORY)
            try:
                os.fsync(directory_fd)
            finally:
                os.close(directory_fd)
        except (OSError, TypeError, ValueError) as exc:
            raise ConfigWriteError(
                "No se pudo guardar la configuracion de vision en {0}: {1}".format(
                    CONFIG_FILE, exc
                )
            ) from exc
        finally:
            if temp_path:
                try:
                    os.unlink(temp_path)
                except OSError:
                    pass


def update_config(mutator):
    """Read, modify and atomically persist the config while holding one lock."""
    with _config_lock:
        config = read_config()
        result = mutator(config)
        write_config(config)
        return config, result
