#!/usr/bin/env python3
"""Focused tests for crash-safe vision configuration persistence."""

import json
import tempfile
import threading
from pathlib import Path

import _bootstrap  # noqa: F401 - adds ffa-app to sys.path
from services import config_store


def test_atomic_read_modify_write():
    with tempfile.TemporaryDirectory() as temp_dir:
        config_path = Path(temp_dir) / "vision_config.json"
        config_path.write_text(json.dumps({"ppmm": 0.23, "zoi": []}), encoding="utf-8")
        original_path = config_store.CONFIG_FILE
        config_store.CONFIG_FILE = config_path
        try:
            config, result = config_store.update_config(
                lambda current: current.__setitem__("ppmm", 0.25)
            )
            assert result is None
            assert config["ppmm"] == 0.25
            assert config_store.read_config()["ppmm"] == 0.25
            assert list(Path(temp_dir).glob("*.tmp")) == []
        finally:
            config_store.CONFIG_FILE = original_path


def test_invalid_json_is_not_silently_accepted():
    with tempfile.TemporaryDirectory() as temp_dir:
        config_path = Path(temp_dir) / "vision_config.json"
        config_path.write_text('{"ppmm":', encoding="utf-8")
        original_path = config_store.CONFIG_FILE
        config_store.CONFIG_FILE = config_path
        try:
            try:
                config_store.read_config()
            except config_store.ConfigStoreError:
                return
            raise AssertionError("Expected ConfigStoreError for corrupted JSON")
        finally:
            config_store.CONFIG_FILE = original_path


def test_non_object_json_is_rejected():
    with tempfile.TemporaryDirectory() as temp_dir:
        config_path = Path(temp_dir) / "vision_config.json"
        config_path.write_text("[]", encoding="utf-8")
        original_path = config_store.CONFIG_FILE
        config_store.CONFIG_FILE = config_path
        try:
            try:
                config_store.read_config()
            except config_store.ConfigReadError:
                return
            raise AssertionError("Expected ConfigReadError for a non-object root")
        finally:
            config_store.CONFIG_FILE = original_path


def test_failed_serialization_preserves_previous_file():
    with tempfile.TemporaryDirectory() as temp_dir:
        config_path = Path(temp_dir) / "vision_config.json"
        original_config = {"ppmm": 0.23}
        config_path.write_text(json.dumps(original_config), encoding="utf-8")
        original_path = config_store.CONFIG_FILE
        config_store.CONFIG_FILE = config_path
        try:
            try:
                config_store.write_config({"invalid": {1, 2, 3}})
            except config_store.ConfigWriteError:
                pass
            else:
                raise AssertionError("Expected ConfigWriteError")
            assert config_store.read_config() == original_config
        finally:
            config_store.CONFIG_FILE = original_path


def test_concurrent_updates_do_not_lose_fields():
    with tempfile.TemporaryDirectory() as temp_dir:
        config_path = Path(temp_dir) / "vision_config.json"
        config_path.write_text("{}", encoding="utf-8")
        original_path = config_store.CONFIG_FILE
        config_store.CONFIG_FILE = config_path
        try:
            threads = []
            for index in range(10):
                thread = threading.Thread(
                    target=config_store.update_config,
                    args=(
                        lambda current, item=index: current.__setitem__(
                            "field_{0}".format(item), item
                        ),
                    ),
                )
                thread.start()
                threads.append(thread)
            for thread in threads:
                thread.join()

            config = config_store.read_config()
            assert len(config) == 10
            for index in range(10):
                assert config["field_{0}".format(index)] == index
        finally:
            config_store.CONFIG_FILE = original_path


def main():
    test_atomic_read_modify_write()
    test_invalid_json_is_not_silently_accepted()
    test_non_object_json_is_rejected()
    test_failed_serialization_preserves_previous_file()
    test_concurrent_updates_do_not_lose_fields()
    print("Config store tests passed")


if __name__ == "__main__":
    main()
