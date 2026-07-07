"""
Request and configuration validation helpers.

This module contains helper functions used to clean, validate, and normalize
values that come from the API request before they are passed into the pipeline.

The main responsibilities of this file are:
- infer the uploaded file type from the filename
- parse the config_json string into a Python dict
- clean optional string inputs
- normalize the selected strategy name
- validate strategy-specific config values

This module does not parse file contents, validate identifier formats, or
generate identifiers. Those steps happen later in the parser, pipeline, and
strategy layers.
"""
import json
from json import JSONDecodeError
from pathlib import Path
from typing import Any


UUID_GENERATION_VERSIONS = {4}  # only 4 for now, can be updated later

CPHI_PCGL_ALLOWED_VARIANTS_BY_TYPE = {
    "patient": {"SPE"},
    "sample": {"EXP", "RG", "ANA", "LIB", "WRK"},
}


def infer_file_type(filename: str | None) -> str:
    """
    Infer the uploaded file type from the filename.

    This function looks at the file extension and converts it into the file type
    string used by the parser.

    For example:
    - "data.csv" becomes "csv"
    - "data.json" becomes "json"
    - "data.xlsx" becomes "xlsx"

    Parameters
    ----------
    filename:
        The name of the uploaded file.

    Returns
    -------
    str:
        The normalized file type that should be passed into the parser.

    Raises
    ------
    ValueError:
        If the filename is missing or if the file extension is not supported.
    """
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
        "Please upload a .csv, .xlsx or .json file."
    )


def parse_config_json(config_json: str) -> dict[str, Any]:
    """
    Parse the config_json request field into a Python dictionary.

    The frontend sends strategy configuration as a JSON string. This function
    converts that string into a Python dict so the backend can validate and use
    the config values.

    Parameters
    ----------
    config_json:
        A JSON string containing strategy-specific configuration values.

    Returns
    -------
    dict:
        The parsed config as a Python dictionary.

    Raises
    ------
    ValueError:
        If config_json is not valid JSON or if the parsed JSON value is not an
        object/dictionary.
    """
    try:
        config = json.loads(config_json)
    except JSONDecodeError:
        raise ValueError("config_json should be a valid JSON input.")

    if not isinstance(config, dict):
        raise ValueError("config_json must be a JSON object.")

    return config


def clean_optional_string(value: str | None) -> str | None:
    """
    Clean an optional string value from the request.

    This function is used for request fields that may be empty, such as an
    optional sheet name or optional column name.

    If the value is None or an empty string after stripping whitespace, this
    function returns None. Otherwise, it returns the stripped string.

    Parameters
    ----------
    value:
        The optional string value to clean.

    Returns
    -------
    str | None:
        The cleaned string, or None if the value is missing or empty.
    """
    if value is None:
        return None

    value = value.strip()

    if value == "":
        return None

    return value


def normalize_strategy_name(strategy_name: str) -> str:
    """
    Normalizes and validates the selected strategy name.

    The function removes whitespace and converts the strategy name to uppercase and checks that it is a supported strategies.
    """
    normalized = strategy_name.strip().upper()

    # Configure this later to add custom or other methods.
    if normalized not in {"CPHI", "UUID", "PCGL","CUSTOM",}:
        raise ValueError("strategy_name must be either 'UUID', 'CPHI', 'PCGL', or 'CUSTOM'.")

    return normalized


def validate_and_normalize_config(
    strategy_name: str,
    config: dict[str, Any],
    mode: str,
) -> dict[str, Any]:
    """
    Validate and normalize the config for the selected strategy.

    This function chooses which strategy-specific config validation function to
    use based on the normalized strategy name.

    For example:
    - UUID uses validate_uuid_config
    - CPHI uses validate_cphi_config
    - PCGL uses validate_pcgl_config
    - CUSTOM uses validate_custom_config

    Parameters
    ----------
    strategy_name:
        The normalized strategy name.

    config:
        A dict containing the config values sent by the frontend.

    mode:
        The current app mode, such as "validate" or "generate".

    Returns
    -------
    dict:
        The validated and normalized config for the selected strategy.

    Raises
    ------
    ValueError:
        If the strategy name is unsupported or if the strategy-specific config
        is invalid.
    """
    if strategy_name == "UUID":
        return validate_uuid_config(config, mode)

    if strategy_name == "CPHI":
        return validate_cphi_config(config, mode)
    if strategy_name == "PCGL":
        return validate_pcgl_config(config, mode)
    if strategy_name == "CUSTOM":
        return validate_custom_config(config, mode)

    raise ValueError(f"Unsupported strategy_name '{strategy_name}'.")


def validate_uuid_config(config: dict[str, Any], mode: str) -> dict[str, Any]:
    """
    Validate and normalize UUID config.

    UUID generation currently requires a version value. For now, only UUID
    version 4 is supported.

    This function accepts the version as either an integer or a numeric string.
    The returned config always stores the version as an integer.

    Parameters
    ----------
    config:
        A dict containing UUID config values.

    mode:
        The current app mode. This parameter is included for consistency with
        the other strategy config validators.

    Returns
    -------
    dict:
        The normalized UUID config.

        Example:
            {
                "version": 4
            }

    Raises
    ------
    ValueError:
        If the version is missing, not an integer, or not supported.
    """
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
    Validate and normalize CPHI config.

    Every CPHI config must include a project code and an entity type. The project
    code is normalized to uppercase and must be exactly 4 alphanumeric
    characters.

    If no entity type is provided, the config defaults to "sample".

    Parameters
    ----------
    config:
        A dict containing CPHI config values.

    mode:
        The current app mode. This parameter is included for consistency with
        the other strategy config validators.

    Returns
    -------
    dict:
        The normalized CPHI config.

        Example:
            {
                "project_code": "NRGI",
                "entity_type": "sample"
            }

    Raises
    ------
    ValueError:
        If project_code is missing, invalid, or if entity_type is not "patient"
        or "sample".
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
        entity_type = "sample" #Defaulting entity_type to sample

    if not isinstance(entity_type, str):
        raise ValueError("entity_type must be a string.")

    entity_type = entity_type.strip().lower()

    if entity_type not in {"patient", "sample"}:
        raise ValueError("entity_type must be either 'patient' or 'sample'.")

    normalized_config: dict[str, Any] = {
        "project_code": project_code,
        "entity_type": entity_type,
    }

    return normalized_config

def validate_pcgl_config(config:dict, mode:str) -> dict:
    """
    Validate and normalize PCGL config.

    Every PCGL config must include a project code and an entity type. The project
    code is normalized to uppercase and must be exactly 4 alphanumeric
    characters.

    The entity type controls which variants are allowed:
    - patient allows SPE
    - sample allows EXP, RG, ANA, LIB, and WRK

    PCGL handles variants differently depending on the mode:

    - In generate mode, the frontend sends plural "variants" as a list because
      the user may want to generate several derived identifier columns.

    - In validate mode, the frontend sends singular "variant" because the user
      is validating one specific PCGL variant format.

    If no variant is provided in validate mode, the config returns only the base
    project code and entity type.

    Parameters
    ----------
    config:
        A dict containing PCGL config values.

    mode:
        The current app mode, such as "validate" or "generate".

    Returns
    -------
    dict:
        The normalized PCGL config.

        Example for validation:
            {
                "project_code": "NRGI",
                "entity_type": "sample",
                "variant": "EXP"
            }

        Example for generation:
            {
                "project_code": "NRGI",
                "entity_type": "sample",
                "variants": ["EXP", "LIB"]
            }

    Raises
    ------
    ValueError:
        If project_code, entity_type, variant, or variants are invalid.
    """

    if "project_code" not in config:
        raise ValueError("Missing 'project_code' in config for PCGL.")

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
        entity_type = "sample" #Defaulting all to sample type

    if not isinstance(entity_type, str):
        raise ValueError("entity_type must be a string.")

    entity_type = entity_type.strip().lower()

    if entity_type not in {"patient", "sample"}:
        raise ValueError("entity_type must be either 'patient' or 'sample'.")

    normalized_config: dict[str, Any] = {
        "project_code": project_code,
        "entity_type": entity_type,
    }

    # Generate mode uses plural variants.
    if mode == "generate":
        variants = config.get("variants", [])

        if variants in (None, ""):
            variants = []

        if not isinstance(variants, list):
            raise ValueError("'variants' must be a list for PCGL generation.")

        normalized_variants = []
        allowed_variants = CPHI_PCGL_ALLOWED_VARIANTS_BY_TYPE[entity_type]

        for variant in variants:
            if not isinstance(variant, str):
                raise ValueError("Each PCGL variant must be a string.")

            variant = variant.strip().upper()

            if variant == "":
                continue

            if variant not in allowed_variants:
                raise ValueError(
                    f"Variant '{variant}' is not allowed for entity_type "
                    f"'{entity_type}'. Allowed variants: {sorted(allowed_variants)}."
                )

            normalized_variants.append(variant)

        if normalized_variants:
            normalized_config["variants"] = normalized_variants

        return normalized_config

    variant = config.get("variant")

    # Variant is optional.
    # If no variant is provided, use base CPHI strategy.
    if variant in (None, ""):
        return normalized_config

    if not isinstance(variant, str):
        raise ValueError("variant must be a string.")

    variant = variant.strip().upper()

    allowed_variants = CPHI_PCGL_ALLOWED_VARIANTS_BY_TYPE[entity_type]

    if variant not in allowed_variants:
        raise ValueError(
            f"Variant '{variant}' is not allowed for entity_type '{entity_type}'. "
            f"Allowed variants: {sorted(allowed_variants)}."
        )

    normalized_config["variant"] = variant

    return normalized_config

def validate_custom_config(config: dict, mode:str) -> dict:
    """
    Validate and normalize custom identifier config.

    This function validates the options used to generate custom identifiers.

    A custom identifier can have either:
    - a random prefix
    - a fixed prefix

    It also validates the connector, suffix type, suffix length, and any prefix
    settings needed for the selected prefix mode.

    Parameters
    ----------
    config:
        A dict containing custom identifier config values.

    mode:
        The current app mode. This parameter is included for consistency with
        the other strategy config validators.

    Returns
    -------
    dict:
        The normalized custom config.

        Example with random prefix:
            {
                "prefix_mode": "random",
                "connector": "-",
                "suffix_type": "numeric",
                "suffix_length": 6,
                "prefix_type": "letters",
                "prefix_length": 4
            }

        Example with fixed prefix:
            {
                "prefix_mode": "fixed",
                "connector": "-",
                "suffix_type": "numeric",
                "suffix_length": 6,
                "fixed_prefix": "TEST"
            }

    Raises
    ------
    ValueError:
        If any custom config field is missing, invalid, or not allowed.
    """
    config = config or {}

    allowed_prefix_modes = {"random", "fixed"}
    allowed_connectors = {"-", "_", "", "+"}

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
    """
    Validate and normalize a custom character type field.

    This function is used for fields like prefix_type and suffix_type. It makes
    sure the value is a string and that it belongs to the allowed character
    types.

    Parameters
    ----------
    value:
        The character type value to validate.

        Allowed values are:
        - "alphanumeric"
        - "numeric"
        - "letters"

    field_name:
        The name of the field being checked.

        This is used to make the error message more specific.

    Returns
    -------
    str:
        The normalized character type.

    Raises
    ------
    ValueError:
        If the value is not a string or if it is not one of the allowed character
        types.
    """
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
    """
    Convert a value into a positive integer.

    This function is used for config values that must be positive numbers, such
    as prefix_length and suffix_length.

    Parameters
    ----------
    value:
        The value to convert into an integer.

    field_name:
        The name of the field being checked.

        This is used to make the error message more specific.

    Returns
    -------
    int:
        The normalized positive integer.

    Raises
    ------
    ValueError:
        If the value cannot be converted into an integer or if the integer is
        less than or equal to 0.
    """
    try:
        normalized = int(value)
    except (TypeError, ValueError):
        raise ValueError(f"'{field_name}' must be an integer.")

    if normalized <= 0:
        raise ValueError(f"'{field_name}' must be greater than 0.")

    return normalized