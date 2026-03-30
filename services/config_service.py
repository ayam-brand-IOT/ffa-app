"""
config_service.py
-----------------
Business logic for reading and updating vision/fish configuration.
Used by both the HTTP routes and the SocketIO handlers.
"""

import json
import imageProcess
from logger import logEvent

CONFIG_FILE = "./vision_config.json"


def _read_config() -> dict:
    with open(CONFIG_FILE, "r") as f:
        return json.load(f)


def _write_config(config: dict) -> None:
    with open(CONFIG_FILE, "w") as f:
        json.dump(config, f, indent=2)


def update_fish_params(data: dict) -> dict:
    """
    Receives:  { "fish_species": "mackerel", "type": "HG" }
    Finds the matching species/type in vision_config.json, applies the
    parameters to imageProcess, and returns the result.
    """
    species_name = data.get("fish_species")
    type_name = data.get("type")
    print("Solicitud para actualizar parámetros para especie:", species_name, "y tipo:", type_name)

    try:
        config = _read_config()
    except Exception as e:
        error_msg = f"Error al leer vision_config.json: {e}"
        print(error_msg)
        logEvent(etapa="CONFIG_UPDATE", status="ERROR",
                 error_code="CONFIG_READ_ERROR", error_msg=error_msg)
        return {"error": error_msg}

    for species in config.get("species_params", []):
        if species.get("name") == species_name:
            for tipo in species.get("types", []):
                if tipo.get("typeName") == type_name:
                    params = tipo.get("parameters")
                    imageProcess.update_fish_parameters(params)
                    print("Parámetros actualizados en imageProcess:", params)
                    logEvent(
                        etapa="CONFIG_UPDATE", status="SUCCESS",
                        fish_params={"species": species_name, "type": type_name, "parameters": params},
                        additional_data={"config_type": "fish_parameters"},
                    )
                    return {"status": "ok", "parameters": params}

    logEvent(
        etapa="CONFIG_UPDATE", status="ERROR",
        error_code="SPECIES_NOT_FOUND",
        error_msg=f"Especie '{species_name}' o tipo '{type_name}' no encontrado",
        fish_params={"species": species_name, "type": type_name},
    )
    return {"error": "Especie o tipo no encontrado"}


def update_config(data: dict) -> tuple:
    """
    Updates tailTrigger and/or species_params in vision_config.json.
    Returns (response_dict, http_status_code).
    """
    if not data:
        return {"error": "No data provided"}, 400

    try:
        config = _read_config()
        old_config = json.loads(json.dumps(config))
    except Exception as e:
        error_msg = f"Error reading config file: {e}"
        logEvent(etapa="CONFIG_UPDATE", status="ERROR",
                 error_code="CONFIG_READ_ERROR", error_msg=error_msg)
        return {"error": error_msg}, 500

    updated_fields = []

    if "tailTrigger" in data:
        config["tailTrigger"] = data["tailTrigger"]
        updated_fields.append("tailTrigger")

    if "species_params" in data:
        species_data = data["species_params"]
        required_fields = ["name", "typeName", "parameters"]
        if not all(field in species_data for field in required_fields):
            return {"error": "species_params must contain name, typeName, and parameters"}, 400

        species_name = species_data["name"]
        type_name = species_data["typeName"]
        new_parameters = species_data["parameters"]
        found = False

        for species in config.get("species_params", []):
            if species.get("name") == species_name:
                for fish_type in species.get("types", []):
                    if fish_type.get("typeName") == type_name:
                        fish_type["parameters"] = new_parameters
                        found = True
                        updated_fields.append(f"species_params.{species_name}.{type_name}")
                        break
                if found:
                    break

        if not found:
            return {"error": f"Species '{species_name}' with type '{type_name}' not found"}, 404

    try:
        _write_config(config)
        logEvent(
            etapa="CONFIG_UPDATE", status="SUCCESS",
            vision_params=config.get("vision_params"),
            fish_params=data.get("species_params"),
            additional_data={
                "updated_fields": updated_fields,
                "old_tailTrigger": old_config.get("tailTrigger") if "tailTrigger" in updated_fields else None,
                "new_tailTrigger": config.get("tailTrigger") if "tailTrigger" in updated_fields else None,
            },
        )
    except Exception as e:
        error_msg = f"Error writing config file: {e}"
        logEvent(etapa="CONFIG_UPDATE", status="ERROR",
                 error_code="CONFIG_WRITE_ERROR", error_msg=error_msg)
        return {"error": error_msg}, 500

    return {
        "status": "success",
        "message": "Configuration updated successfully",
        "updated_fields": updated_fields,
        "config": config,
    }, 200


def get_config() -> tuple:
    """Returns the current config as (dict, status_code)."""
    try:
        config = _read_config()
        return config, 200
    except Exception as e:
        return {"error": f"Error reading config: {str(e)}"}, 500
