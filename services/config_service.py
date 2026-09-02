"""Business logic for reading and updating vision/fish configuration."""

import json
import math

import imageProcess
from logger import logEvent
from services.config_store import (
    ConfigReadError,
    ConfigStoreError,
    ConfigWriteError,
    read_config,
    update_config as update_config_backend,
)


def _read_config():
    return read_config()


def update_fish_params(data: dict) -> dict:
    """Apply the selected species/type parameters to the active analysis session."""
    if not isinstance(data, dict):
        return {"error": "Fish selection must be an object", "_http_status": 400}

    species_name = data.get("fish_species")
    type_name = data.get("type")
    if not species_name or not type_name:
        return {"error": "fish_species and type are required", "_http_status": 400}

    try:
        config = _read_config()
    except ConfigReadError as exc:
        error_msg = str(exc)
        logEvent(
            etapa="CONFIG_UPDATE",
            status="ERROR",
            error_code="CONFIG_READ_ERROR",
            error_msg=error_msg,
        )
        return {"error": error_msg, "_http_status": 500}

    for species in config.get("species_params", []):
        if species.get("name") != species_name:
            continue
        for fish_type in species.get("types", []):
            if fish_type.get("typeName") != type_name:
                continue
            params = fish_type.get("parameters")
            try:
                imageProcess.update_fish_parameters(params)
            except ValueError as exc:
                error_msg = str(exc)
                logEvent(
                    etapa="CONFIG_UPDATE",
                    status="ERROR",
                    error_code="FISH_PARAMETERS_INVALID",
                    error_msg=error_msg,
                    fish_params={"species": species_name, "type": type_name},
                )
                return {"error": error_msg, "_http_status": 400}
            except ConfigStoreError as exc:
                error_msg = str(exc)
                logEvent(
                    etapa="CONFIG_UPDATE",
                    status="ERROR",
                    error_code="CONFIG_WRITE_ERROR",
                    error_msg=error_msg,
                    fish_params={"species": species_name, "type": type_name},
                )
                return {"error": error_msg, "_http_status": 500}

            logEvent(
                etapa="CONFIG_UPDATE",
                status="SUCCESS",
                fish_params={
                    "species": species_name,
                    "type": type_name,
                    "parameters": params,
                },
                additional_data={"config_type": "fish_parameters"},
            )
            return {"status": "ok", "parameters": params, "_http_status": 200}

    error_msg = "Especie '{0}' o tipo '{1}' no encontrado".format(
        species_name, type_name
    )
    logEvent(
        etapa="CONFIG_UPDATE",
        status="ERROR",
        error_code="SPECIES_NOT_FOUND",
        error_msg=error_msg,
        fish_params={"species": species_name, "type": type_name},
    )
    return {"error": "Especie o tipo no encontrado", "_http_status": 404}


def update_config(data: dict) -> tuple:
    """Update tailTrigger and/or a configured species/type atomically."""
    if not isinstance(data, dict) or not data:
        return {"error": "No data provided"}, 400
    unknown_fields = set(data) - {"tailTrigger", "species_params"}
    if unknown_fields:
        return {
            "error": "Unsupported fields: {0}".format(", ".join(sorted(unknown_fields)))
        }, 400

    tail_trigger = None
    if "tailTrigger" in data:
        if isinstance(data["tailTrigger"], bool):
            return {"error": "tailTrigger must be numeric"}, 400
        try:
            tail_trigger = float(data["tailTrigger"])
        except (TypeError, ValueError) as exc:
            return {"error": "tailTrigger must be numeric"}, 400
        if not math.isfinite(tail_trigger) or not 0 <= tail_trigger <= 650:
            return {"error": "tailTrigger must be between 0 and 650"}, 400

    species_data = data.get("species_params")
    if species_data is not None:
        required_fields = {"name", "typeName", "parameters"}
        if not isinstance(species_data, dict) or not required_fields.issubset(species_data):
            return {"error": "species_params must contain name, typeName, parameters"}, 400
        try:
            normalized_parameters = imageProcess.validate_fish_parameters(
                species_data["parameters"]
            )
        except ValueError as exc:
            return {"error": str(exc)}, 400

    old_config = None

    def mutate(config):
        nonlocal old_config
        old_config = json.loads(json.dumps(config))
        updated_fields = []
        if "tailTrigger" in data:
            config["tailTrigger"] = tail_trigger
            updated_fields.append("tailTrigger")

        if species_data is not None:
            for species in config.get("species_params", []):
                if species.get("name") != species_data["name"]:
                    continue
                for fish_type in species.get("types", []):
                    if fish_type.get("typeName") == species_data["typeName"]:
                        fish_type["parameters"] = normalized_parameters
                        updated_fields.append(
                            "species_params.{0}.{1}".format(
                                species_data["name"], species_data["typeName"]
                            )
                        )
                        return updated_fields
            raise LookupError("Species/type not found")

        return updated_fields

    try:
        config, updated_fields = update_config_backend(mutate)
    except LookupError:
        return {"error": "Species/type not found"}, 404
    except ConfigReadError as exc:
        error_msg = str(exc)
        logEvent(
            etapa="CONFIG_UPDATE",
            status="ERROR",
            error_code="CONFIG_READ_ERROR",
            error_msg=error_msg,
        )
        return {"error": error_msg}, 500
    except ConfigWriteError as exc:
        error_msg = str(exc)
        logEvent(
            etapa="CONFIG_UPDATE",
            status="ERROR",
            error_code="CONFIG_WRITE_ERROR",
            error_msg=error_msg,
        )
        return {"error": error_msg}, 500

    logEvent(
        etapa="CONFIG_UPDATE",
        status="SUCCESS",
        vision_params=config.get("vision_params"),
        fish_params=species_data,
        additional_data={
            "updated_fields": updated_fields,
            "old_tailTrigger": old_config.get("tailTrigger")
            if "tailTrigger" in updated_fields
            else None,
            "new_tailTrigger": config.get("tailTrigger")
            if "tailTrigger" in updated_fields
            else None,
        },
    )
    return {
        "status": "success",
        "message": "Configuration updated successfully",
        "updated_fields": updated_fields,
        "config": config,
    }, 200


def get_config() -> tuple:
    try:
        return _read_config(), 200
    except ConfigStoreError as exc:
        return {"error": "Error reading config: {0}".format(exc)}, 500
