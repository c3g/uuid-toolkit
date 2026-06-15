import json
from json import JSONDecodeError
from pathlib import Path
from typing import Any


UUID_GENERATION_VERSIONS = {4}  # only 4 for now, can be updated later

CPHI_ALLOWED_VARIANTS_BY_TYPE = {
    "patient": {"SPE"},
    "sample": {"EXP", "RG", "ANA", "LIB", "WRK"},
}


def infer_file_type(filename: str | None) -> str:
    if not filename:
        raise ValueError("The uploaded file must contain a name.")

    suffix = Path(filename).suffix.lower()

    if suffix == ".csv":
        return "csv"

    if suffix == ".json":
        return "json"
    if suffix == ".xlsx":
        return "xlsx"

    raise ValueError(
        f"Unsupported file type/extension '{suffix}'. "
        "Please upload a .csv or .json file."
    )


def parse_config_json(config_json: str) -> dict[str, Any]:
    try:
        config = json.loads(config_json)
    except JSONDecodeError:
        raise ValueError("config_json should be a valid JSON input.")

    if not isinstance(config, dict):
        raise ValueError("config_json must be a JSON object.")

    return config


def clean_optional_string(value: str | None) -> str | None:
    if value is None:
        return None

    value = value.strip()

    if value == "":
        return None

    return value


def normalize_strategy_name(strategy_name: str) -> str:
    normalized = strategy_name.strip().upper()

    # Configure this later to add custom or other methods.
    if normalized not in {"CPHI", "UUID", "CUSTOM",}:
        raise ValueError("strategy_name must be either 'UUID', 'CPHI', or 'CUSTOM'.")

    return normalized


def validate_and_normalize_config(
    strategy_name: str,
    config: dict[str, Any],
    mode: str,
) -> dict[str, Any]:
    if strategy_name == "UUID":
        return validate_uuid_config(config, mode)

    if strategy_name == "CPHI":
        return validate_cphi_config(config, mode)
    if strategy_name == "CUSTOM":
        return validate_custom_config(config, mode)

    raise ValueError(f"Unsupported strategy_name '{strategy_name}'.")


def validate_uuid_config(config: dict[str, Any], mode: str) -> dict[str, Any]:
    if "version" not in config:
        raise ValueError("Missing 'version' in config for UUID.")

    version = config["version"]

    if isinstance(version, str):
        if not version.isdigit():
            raise ValueError("UUID version must be an integer.")
        version = int(version)

    if not isinstance(version, int):
        raise ValueError("UUID version must be an integer.")

    if version not in UUID_GENERATION_VERSIONS:
        raise ValueError(
            f"Unsupported UUID version '{version}'. "
            f"Supported versions: {sorted(UUID_GENERATION_VERSIONS)}."
        )

    return {
        "version": version,
    }


def validate_cphi_config(config: dict[str, Any], mode: str) -> dict[str, Any]:
    """
    Validate CPHI config.

    Every CPHI ID must belong to an entity type:
    - patient
    - sample

    A variant is optional.
    """

    if "project_code" not in config:
        raise ValueError("Missing 'project_code' in config for CPHI.")

    project_code = config["project_code"]

    if not isinstance(project_code, str):
        raise ValueError("project_code must be a string.")

    project_code = project_code.strip().upper()

    if len(project_code) != 4:
        raise ValueError("project_code must be exactly 4 characters.")

    if not project_code.isalnum():
        raise ValueError("project_code must be alphanumeric.")

    entity_type = config.get("entity_type")

    if entity_type in (None, ""):
        raise ValueError(
            "entity_type is required for CPHI. Choose 'patient' or 'sample'."
        )

    if not isinstance(entity_type, str):
        raise ValueError("entity_type must be a string.")

    entity_type = entity_type.strip().lower()

    if entity_type not in {"patient", "sample"}:
        raise ValueError("entity_type must be either 'patient' or 'sample'.")

    normalized_config: dict[str, Any] = {
        "project_code": project_code,
        "entity_type": entity_type,
    }

    variant = config.get("variant")

    # Variant is optional.
    # If no variant is provided, use base CPHI strategy.
    if variant in (None, ""):
        return normalized_config

    if not isinstance(variant, str):
        raise ValueError("variant must be a string.")

    variant = variant.strip().upper()

    allowed_variants = CPHI_ALLOWED_VARIANTS_BY_TYPE[entity_type]

    if variant not in allowed_variants:
        raise ValueError(
            f"Variant '{variant}' is not allowed for entity_type '{entity_type}'. "
            f"Allowed variants: {sorted(allowed_variants)}."
        )

    normalized_config["variant"] = variant

    return normalized_config
def validate_custom_config(config: dict) -> dict:
    config = config or {}

    allowed_prefix_modes = {"random", "fixed"}
    allowed_char_types = {"alphanumeric", "numeric", "letters"}
    allowed_connectors = {"-", "_", ""}

    prefix_mode = config.get("prefix_mode", "random")

    if not isinstance(prefix_mode, str):
        raise ValueError("'prefix_mode' must be a string.")

    prefix_mode = prefix_mode.strip().lower()

    if prefix_mode not in allowed_prefix_modes:
        raise ValueError(
            f"Invalid prefix_mode '{prefix_mode}'. "
            f"Allowed values: {sorted(allowed_prefix_modes)}."
        )

    connector = config.get("connector", "")

    if connector is None:
        connector = ""

    if not isinstance(connector, str):
        raise ValueError("'connector' must be a string.")

    connector = connector.strip()

    if connector.lower() == "none":
        connector = ""

    if connector not in allowed_connectors:
        raise ValueError("Invalid connector. Allowed values are '-', '_', or empty.")

    suffix_type = normalize_custom_char_type(
        config.get("suffix_type"),
        "suffix_type",
    )

    suffix_length = normalize_positive_int(
        config.get("suffix_length"),
        "suffix_length",
    )

    normalized_config = {
        "prefix_mode": prefix_mode,
        "connector": connector,
        "suffix_type": suffix_type,
        "suffix_length": suffix_length,
    }

    if prefix_mode == "fixed":
        fixed_prefix = config.get("fixed_prefix")

        if not isinstance(fixed_prefix, str):
            raise ValueError(
                "'fixed_prefix' must be a string when prefix_mode is 'fixed'."
            )

        fixed_prefix = fixed_prefix.strip()

        if fixed_prefix == "":
            raise ValueError("'fixed_prefix' cannot be empty.")

        if not fixed_prefix.isalnum():
            raise ValueError("'fixed_prefix' must contain only letters and numbers.")

        normalized_config["fixed_prefix"] = fixed_prefix
        return normalized_config

    prefix_type = normalize_custom_char_type(
        config.get("prefix_type"),
        "prefix_type",
    )

    prefix_length = normalize_positive_int(
        config.get("prefix_length"),
        "prefix_length",
    )

    normalized_config["prefix_type"] = prefix_type
    normalized_config["prefix_length"] = prefix_length

    return normalized_config


def normalize_custom_char_type(value, field_name: str) -> str:
    allowed_char_types = {"alphanumeric", "numeric", "letters"}

    if not isinstance(value, str):
        raise ValueError(f"'{field_name}' must be a string.")

    normalized = value.strip().lower()

    if normalized not in allowed_char_types:
        raise ValueError(
            f"Invalid {field_name} '{value}'. "
            f"Allowed values: {sorted(allowed_char_types)}."
        )

    return normalized


def normalize_positive_int(value, field_name: str) -> int:
    try:
        normalized = int(value)
    except (TypeError, ValueError):
        raise ValueError(f"'{field_name}' must be an integer.")

    if normalized <= 0:
        raise ValueError(f"'{field_name}' must be greater than 0.")

    return normalized