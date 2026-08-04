"""
Helpers for cleaning and validating API request values.

The validation and generation routes use this file before calling the pipeline.
It handles request-level values such as file extensions, strategy names, and
strategy config. It does not validate identifier formats or read file contents.

Main flow:

    ToolkitPage.jsx
        -> generate.py or validate.py
        -> functions in this file
        -> pipeline.py
        -> registry.py
        -> selected strategy

How this file connects to the project
-------------------------------------
- ``generate.py`` and ``validate.py`` use these helpers before running a
  pipeline.
- ``registry.py`` receives the normalized strategy name and config.
- Strategy files use the normalized config when validating or generating IDs.
- ``ConfigPanel.jsx`` collects the options handled here.
- ``ToolkitPage.jsx`` builds ``config_json`` and sends it to the backend.

Adding a new strategy
---------------------
1. Add the strategy name to ``SUPPORTED_STRATEGIES``.
2. Add a config validation function for the new strategy.
3. Add its branch to ``validate_and_normalize_config()``.
4. Register the strategy in ``registry.py``.
5. Add its controls to ``ConfigPanel.jsx``.
6. Update ``ToolkitPage.jsx`` so ``buildConfig()`` sends the required values.
7. Add API, strategy, and pipeline tests.
"""

import json
from json import JSONDecodeError
from pathlib import Path
from typing import Any


SUPPORTED_STRATEGIES = {
    "UUID",
    "CPHI",
    "PCGL",
    "CUSTOM",
}

SUPPORTED_UUID_VERSIONS = {
    4,
}

ALLOWED_ENTITY_TYPES = {
    "patient",
    "sample",
}

ALLOWED_PCGL_VARIANTS_BY_ENTITY_TYPE = {
    "patient": {"SPE"},
    "sample": {"EXP", "RG", "ANA", "LIB", "WRK"},
}

ALLOWED_CUSTOM_PREFIX_MODES = {
    "random",
    "fixed",
}

ALLOWED_CUSTOM_CONNECTORS = {
    "-",
    "_",
    "+",
    "",
}

ALLOWED_CUSTOM_CHAR_TYPES = {
    "alphanumeric",
    "numeric",
    "letters",
}


def infer_file_type(filename: str | None) -> str:
    """
    Return the parser file type based on an uploaded filename.

    Parameters
    ----------
    filename:
        Uploaded filename, including its extension.

    Returns
    -------
    str
        ``"csv"``, ``"json"``, or ``"xlsx"``.

    Raises
    ------
    ValueError
        Raised when the filename is missing or its extension is unsupported.
    """
    if not filename:
        raise ValueError(
            "The uploaded file must contain a name."
        )

    suffix = Path(filename).suffix.lower()

    supported_extensions = {
        ".csv": "csv",
        ".json": "json",
        ".xlsx": "xlsx",
    }

    try:
        return supported_extensions[suffix]
    except KeyError as error:
        raise ValueError(
            f"Unsupported file extension '{suffix}'. "
            "Please upload a .csv, .xlsx, or .json file."
        ) from error


def parse_config_json(
    config_json: str,
) -> dict[str, Any]:
    """
    Convert the frontend ``config_json`` field into a Python dictionary.

    Raises
    ------
    ValueError
        Raised when the value is not valid JSON or does not contain a JSON
        object.
    """
    try:
        config = json.loads(config_json)
    except JSONDecodeError as error:
        raise ValueError(
            "config_json must contain valid JSON."
        ) from error

    if not isinstance(config, dict):
        raise ValueError(
            "config_json must be a JSON object."
        )

    return config


def clean_optional_string(
    value: str | None,
) -> str | None:
    """
    Strip an optional string and return ``None`` when it is empty.
    """
    if value is None:
        return None

    cleaned_value = value.strip()

    if cleaned_value == "":
        return None

    return cleaned_value


def normalize_strategy_name(
    strategy_name: str,
) -> str:
    """
    Normalize and validate a strategy name from an API request.

    Returns
    -------
    str
        Uppercase strategy name.

    Raises
    ------
    ValueError
        Raised when the value is not a supported strategy name.
    """
    if not isinstance(strategy_name, str):
        raise ValueError(
            "strategy_name must be a string."
        )

    normalized = strategy_name.strip().upper()

    if normalized not in SUPPORTED_STRATEGIES:
        raise ValueError(
            f"Unsupported strategy_name '{strategy_name}'. "
            f"Supported values: {sorted(SUPPORTED_STRATEGIES)}."
        )

    return normalized


def validate_and_normalize_config(
    strategy_name: str,
    config: dict[str, Any],
    mode: str,
) -> dict[str, Any]:
    """
    Validate the config for the selected strategy and request mode.

    Parameters
    ----------
    strategy_name:
        Normalized strategy name.

    config:
        Config values received from the frontend.

    mode:
        ``"validate"`` or ``"generate"``.

    Returns
    -------
    dict[str, Any]
        Config with normalized values ready for the registry and pipeline.

    Raises
    ------
    ValueError
        Raised when the mode, strategy, or strategy config is invalid.
    """
    if mode not in {"validate", "generate"}:
        raise ValueError(
            "mode must be either 'validate' or 'generate'."
        )

    config_validators = {
        "UUID": validate_uuid_config,
        "CPHI": validate_cphi_config,
        "PCGL": validate_pcgl_config,
        "CUSTOM": validate_custom_config,
    }

    try:
        validator = config_validators[strategy_name]
    except KeyError as error:
        raise ValueError(
            f"Unsupported strategy_name '{strategy_name}'."
        ) from error

    return validator(config, mode)


def validate_uuid_config(
    config: dict[str, Any],
    mode: str,
) -> dict[str, Any]:
    """
    Validate UUID config and normalize ``version`` to an integer.

    The ``mode`` parameter is kept so all strategy config validators use the
    same function signature.
    """
    if "version" not in config:
        raise ValueError(
            "Missing 'version' in config for UUID."
        )

    version = config["version"]

    if isinstance(version, str):
        cleaned_version = version.strip()

        if not cleaned_version.isdigit():
            raise ValueError(
                "UUID version must be an integer."
            )

        version = int(cleaned_version)

    if (
        not isinstance(version, int)
        or isinstance(version, bool)
    ):
        raise ValueError(
            "UUID version must be an integer."
        )

    if version not in SUPPORTED_UUID_VERSIONS:
        raise ValueError(
            f"Unsupported UUID version '{version}'. "
            f"Supported versions: "
            f"{sorted(SUPPORTED_UUID_VERSIONS)}."
        )

    return {
        "version": version,
    }


def validate_cphi_config(
    config: dict[str, Any],
    mode: str,
) -> dict[str, Any]:
    """
    Validate config for a CPHI identifier.

    CPHI requires a four-character project code and an entity type. The entity
    type defaults to ``"sample"`` when it is not provided.

    The ``mode`` parameter is kept so all strategy config validators use the
    same function signature.
    """
    project_code = normalize_project_code(
        config.get("project_code"),
        strategy_name="CPHI",
    )

    entity_type = normalize_entity_type(
        config.get("entity_type"),
    )

    return {
        "project_code": project_code,
        "entity_type": entity_type,
    }


def validate_pcgl_config(
    config: dict[str, Any],
    mode: str,
) -> dict[str, Any]:
    """
    Validate config for a base or modified PCGL identifier.

    In validation mode, ``variant`` is singular because one identifier format
    is checked at a time.

    In generation mode, ``variants`` is a list because several variant columns
    can be derived from one existing base PCGL ID.

    When no variant is selected, the config represents the base PCGL format.
    """
    project_code = normalize_project_code(
        config.get("project_code"),
        strategy_name="PCGL",
    )

    entity_type = normalize_entity_type(
        config.get("entity_type"),
    )

    normalized_config: dict[str, Any] = {
        "project_code": project_code,
        "entity_type": entity_type,
    }

    if mode == "generate":
        variants = config.get("variants", [])

        if variants in (None, ""):
            variants = []

        if not isinstance(variants, list):
            raise ValueError(
                "'variants' must be a list for PCGL generation."
            )

        normalized_variants: list[str] = []

        for variant in variants:
            normalized_variant = normalize_pcgl_variant(
                variant,
                entity_type=entity_type,
            )

            # Keep the frontend order while avoiding duplicate output columns.
            if normalized_variant not in normalized_variants:
                normalized_variants.append(
                    normalized_variant
                )

        if normalized_variants:
            normalized_config["variants"] = (
                normalized_variants
            )

        return normalized_config

    variant = config.get("variant")

    if variant in (None, ""):
        return normalized_config

    normalized_config["variant"] = (
        normalize_pcgl_variant(
            variant,
            entity_type=entity_type,
        )
    )

    return normalized_config


def validate_custom_config(
    config: dict[str, Any],
    mode: str,
) -> dict[str, Any]:
    """
    Validate config for a user-defined custom identifier format.

    A custom identifier can use either a fixed or random prefix, followed by an
    optional connector and a configured suffix.

    The ``mode`` parameter is kept so all strategy config validators use the
    same function signature.
    """
    config = config or {}

    prefix_mode = config.get(
        "prefix_mode",
        "random",
    )

    if not isinstance(prefix_mode, str):
        raise ValueError(
            "'prefix_mode' must be a string."
        )

    prefix_mode = prefix_mode.strip().lower()

    if prefix_mode not in ALLOWED_CUSTOM_PREFIX_MODES:
        raise ValueError(
            f"Invalid prefix_mode '{prefix_mode}'. "
            f"Allowed values: "
            f"{sorted(ALLOWED_CUSTOM_PREFIX_MODES)}."
        )

    connector = normalize_custom_connector(
        config.get("connector", "")
    )

    suffix_type = normalize_custom_char_type(
        config.get("suffix_type"),
        "suffix_type",
    )

    suffix_length = normalize_positive_int(
        config.get("suffix_length"),
        "suffix_length",
    )

    normalized_config: dict[str, Any] = {
        "prefix_mode": prefix_mode,
        "connector": connector,
        "suffix_type": suffix_type,
        "suffix_length": suffix_length,
    }

    if prefix_mode == "fixed":
        normalized_config["fixed_prefix"] = (
            normalize_fixed_prefix(
                config.get("fixed_prefix")
            )
        )

        return normalized_config

    normalized_config["prefix_type"] = (
        normalize_custom_char_type(
            config.get("prefix_type"),
            "prefix_type",
        )
    )

    normalized_config["prefix_length"] = (
        normalize_positive_int(
            config.get("prefix_length"),
            "prefix_length",
        )
    )

    return normalized_config


def normalize_project_code(
    value: Any,
    *,
    strategy_name: str,
) -> str:
    """
    Normalize a CPHI or PCGL project code.
    """
    if value is None:
        raise ValueError(
            f"Missing 'project_code' in config for "
            f"{strategy_name}."
        )

    if not isinstance(value, str):
        raise ValueError(
            "project_code must be a string."
        )

    project_code = value.strip().upper()

    if len(project_code) != 4:
        raise ValueError(
            "project_code must be exactly 4 characters."
        )

    if not project_code.isalnum():
        raise ValueError(
            "project_code must be alphanumeric."
        )

    return project_code


def normalize_entity_type(
    value: Any,
) -> str:
    """
    Normalize a CPHI or PCGL entity type.

    Missing values default to ``"sample"``.
    """
    if value in (None, ""):
        value = "sample"

    if not isinstance(value, str):
        raise ValueError(
            "entity_type must be a string."
        )

    entity_type = value.strip().lower()

    if entity_type not in ALLOWED_ENTITY_TYPES:
        raise ValueError(
            "entity_type must be either "
            "'patient' or 'sample'."
        )

    return entity_type


def normalize_pcgl_variant(
    value: Any,
    *,
    entity_type: str,
) -> str:
    """
    Normalize one PCGL variant and check it against the entity type.
    """
    if not isinstance(value, str):
        raise ValueError(
            "Each PCGL variant must be a string."
        )

    variant = value.strip().upper()

    if variant == "":
        raise ValueError(
            "PCGL variants cannot be empty."
        )

    allowed_variants = (
        ALLOWED_PCGL_VARIANTS_BY_ENTITY_TYPE[
            entity_type
        ]
    )

    if variant not in allowed_variants:
        raise ValueError(
            f"Variant '{variant}' is not allowed for "
            f"entity_type '{entity_type}'. "
            f"Allowed variants: {sorted(allowed_variants)}."
        )

    return variant


def normalize_custom_connector(
    value: Any,
) -> str:
    """
    Normalize the connector used between a custom prefix and suffix.

    ``None`` and the string ``"none"`` are treated as no connector.
    """
    if value is None:
        value = ""

    if not isinstance(value, str):
        raise ValueError(
            "'connector' must be a string."
        )

    connector = value.strip()

    if connector.lower() == "none":
        connector = ""

    if connector not in ALLOWED_CUSTOM_CONNECTORS:
        raise ValueError(
            f"Invalid connector '{value}'. "
            f"Allowed values: "
            f"{sorted(ALLOWED_CUSTOM_CONNECTORS)}."
        )

    return connector


def normalize_custom_char_type(
    value: Any,
    field_name: str,
) -> str:
    """
    Normalize a custom prefix or suffix character type.
    """
    if not isinstance(value, str):
        raise ValueError(
            f"'{field_name}' must be a string."
        )

    normalized = value.strip().lower()

    if normalized not in ALLOWED_CUSTOM_CHAR_TYPES:
        raise ValueError(
            f"Invalid {field_name} '{value}'. "
            f"Allowed values: "
            f"{sorted(ALLOWED_CUSTOM_CHAR_TYPES)}."
        )

    return normalized


def normalize_positive_int(
    value: Any,
    field_name: str,
) -> int:
    """
    Convert a length value into a positive integer.
    """
    if isinstance(value, bool):
        raise ValueError(
            f"'{field_name}' must be an integer."
        )

    try:
        normalized = int(value)
    except (TypeError, ValueError) as error:
        raise ValueError(
            f"'{field_name}' must be an integer."
        ) from error

    if normalized <= 0:
        raise ValueError(
            f"'{field_name}' must be greater than 0."
        )

    return normalized


def normalize_fixed_prefix(
    value: Any,
) -> str:
    """
    Normalize the prefix used by fixed-prefix CUSTOM identifiers.
    """
    if not isinstance(value, str):
        raise ValueError(
            "'fixed_prefix' must be a string when "
            "prefix_mode is 'fixed'."
        )

    fixed_prefix = value.strip()

    if fixed_prefix == "":
        raise ValueError(
            "'fixed_prefix' cannot be empty."
        )

    if not fixed_prefix.isalnum():
        raise ValueError(
            "'fixed_prefix' must contain only "
            "letters and numbers."
        )

    return fixed_prefix