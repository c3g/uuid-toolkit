"""
Registry for selecting and creating identifier strategies.

The pipeline calls ``get_strategy()`` with the strategy name and config received
from the API. The registry checks the config needed to select the correct
strategy, then returns an object that follows ``StrategyInterface``.

The main flow is:

    ToolkitPage.jsx
        -> FastAPI endpoint
        -> pipeline
        -> get_strategy()
        -> concrete strategy

Responsibilities are split across the project:

- This file selects and creates the correct strategy.
- Strategy files validate identifier formats and generate candidate IDs.
- The pipeline handles file duplicates and database conflicts.
- ``ConfigPanel.jsx`` collects strategy-specific options.
- ``ToolkitPage.jsx`` builds the config sent to the backend.

Adding a new strategy
---------------------
Backend:
1. Create a strategy class that inherits ``StrategyInterface``.
2. Import the class into this file.
3. Add the strategy name to ``get_strategy()``.
4. Add a helper that checks its config and creates the strategy.
5. Update API config validation when new fields are required.
6. Add validation, generation, and pipeline tests.

Frontend:
1. Add the strategy to the selector in ``ConfigPanel.jsx``.
2. Add any controls required by the strategy.
3. Update ``ToolkitPage.jsx`` so ``buildConfig()`` sends the correct values.
4. Update strategy descriptions and confirmation details when needed.
"""

from .base import StrategyInterface
from .cphi import CPHIStrategy
from .custom import CustomStrategy
from .pcgl import PCGLStrategy
from .pcgl_modifiers import PCGL_Modifiers
from .uuid_standard import UUIDStrategy


_ALLOWED_ENTITY_TYPES = {
    "patient",
    "sample",
}

_ALLOWED_PCGL_VARIANTS_BY_ENTITY_TYPE = {
    "patient": {"SPE"},
    "sample": {"EXP", "RG", "ANA", "LIB", "WRK"},
}

_ALLOWED_UUID_VERSIONS = {
    4,
}


def get_strategy(
    strategy_name: str,
    config: dict | None = None,
) -> StrategyInterface:
    """
    Return the strategy selected by the user.

    Parameters
    ----------
    strategy_name:
        Identifier family to use. Supported values are ``UUID``, ``CPHI``,
        ``PCGL``, and ``CUSTOM``.

    config:
        Strategy-specific configuration.

        Examples:

        UUID:

            {
                "version": 4,
            }

        CPHI:

            {
                "project_code": "NRGI",
                "entity_type": "sample",
            }

        PCGL with one variant:

            {
                "project_code": "NRGI",
                "entity_type": "sample",
                "variant": "EXP",
            }

        PCGL derived generation:

            {
                "project_code": "NRGI",
                "entity_type": "sample",
                "variants": ["EXP", "LIB"],
            }

        CUSTOM:

            {
                "prefix_mode": "random",
                "prefix_type": "letters",
                "prefix_length": 4,
                "connector": "-",
                "suffix_type": "numeric",
                "suffix_length": 6,
            }

    Returns
    -------
    StrategyInterface
        Fully configured strategy object.

    Raises
    ------
    ValueError
        Raised when the strategy name or required config is invalid.
    """
    if not isinstance(strategy_name, str):
        raise ValueError("'strategy_name' must be a string.")

    normalized_name = strategy_name.strip().upper()

    if normalized_name == "":
        raise ValueError("'strategy_name' cannot be empty.")

    config = config or {}

    if normalized_name == "UUID":
        return get_uuid_strategy(config)

    if normalized_name == "CPHI":
        return get_cphi_strategy(config)

    if normalized_name == "PCGL":
        return get_pcgl_strategy(config)

    if normalized_name == "CUSTOM":
        return get_custom_strategy(config)

    raise ValueError(
        f"Strategy name '{normalized_name}' was not found in the registry."
    )


def get_uuid_strategy(
    config: dict,
) -> StrategyInterface:
    """
    Create the UUID strategy for a supported UUID version.

    ``UUIDStrategy`` contains the actual validation and generation logic. This
    function only checks that the requested version is supported.
    """
    if "version" not in config:
        raise ValueError("Missing 'version' in config for UUID strategy.")

    version = config["version"]

    if not isinstance(version, int) or isinstance(version, bool):
        raise ValueError("'version' must be an integer.")

    if version not in _ALLOWED_UUID_VERSIONS:
        raise ValueError(
            f"UUID version {version} is not supported. "
            f"Allowed values: {sorted(_ALLOWED_UUID_VERSIONS)}."
        )

    return UUIDStrategy()


def get_cphi_strategy(
    config: dict,
) -> StrategyInterface:
    """
    Create the base CPHI strategy.

    CPHI identifiers in this toolkit do not use variants. Modified identifiers
    belong to the PCGL strategy.
    """
    _validate_project_strategy_config(
        config,
        strategy_name="CPHI",
    )

    return CPHIStrategy()


def get_pcgl_strategy(
    config: dict,
) -> StrategyInterface:
    """
    Choose the base or modifier PCGL strategy.

    Selection rules:

    - No ``variant`` or ``variants`` returns ``PCGLStrategy``.
    - One ``variant`` returns ``PCGL_Modifiers`` for normal generation.
    - A non-empty ``variants`` list returns ``PCGL_Modifiers`` for derived
      generation from an existing base PCGL identifier.

    ``get_strategy_info()`` inside ``PCGL_Modifiers`` later tells the pipeline
    whether it should use normal or derived generation.
    """
    entity_type = _validate_project_strategy_config(
        config,
        strategy_name="PCGL",
    )

    variant = config.get("variant")
    variants = config.get("variants")

    # A plural variants list means several IDs will be derived from one
    # existing base PCGL identifier.
    if isinstance(variants, list) and len(variants) > 0:
        _validate_pcgl_variants(
            variants,
            entity_type=entity_type,
        )

        return PCGL_Modifiers()

    if _is_blank(variant):
        return PCGLStrategy()

    _validate_pcgl_variant(
        variant,
        entity_type=entity_type,
    )

    return PCGL_Modifiers()


def get_custom_strategy(
    config: dict,
) -> StrategyInterface:
    """
    Create a custom strategy from the selected format options.

    ``CustomStrategy`` performs the detailed normalization and validation of
    prefix, connector, suffix, character type, and length values.
    """
    prefix_mode = config.get(
        "prefix_mode",
        "random",
    )

    connector = config.get(
        "connector",
        "",
    )

    suffix_type = config.get("suffix_type")
    suffix_length = config.get("suffix_length")

    normalized_prefix_mode = (
        prefix_mode.strip().lower()
        if isinstance(prefix_mode, str)
        else prefix_mode
    )

    if normalized_prefix_mode == "fixed":
        return CustomStrategy(
            prefix_mode=normalized_prefix_mode,
            fixed_prefix=config.get("fixed_prefix"),
            connector=connector,
            suffix_type=suffix_type,
            suffix_length=suffix_length,
        )

    return CustomStrategy(
        prefix_mode=normalized_prefix_mode,
        prefix_type=config.get("prefix_type"),
        prefix_length=config.get("prefix_length"),
        connector=connector,
        suffix_type=suffix_type,
        suffix_length=suffix_length,
    )


def _validate_project_strategy_config(
    config: dict,
    *,
    strategy_name: str,
) -> str:
    """
    Validate the config shared by CPHI and PCGL.

    Both strategies require a project code and an entity type. The normalized
    entity type is returned because PCGL uses it to decide which variants are
    allowed.
    """
    project_code = config.get("project_code")
    entity_type = config.get("entity_type")

    if _is_blank(project_code):
        raise ValueError(
            f"Missing 'project_code' in config for {strategy_name} strategy."
        )

    if not isinstance(project_code, str):
        raise ValueError("'project_code' must be a string.")

    if _is_blank(entity_type):
        raise ValueError(
            f"Missing 'entity_type' in config for {strategy_name} strategy. "
            "Expected 'patient' or 'sample'."
        )

    if not isinstance(entity_type, str):
        raise ValueError("'entity_type' must be a string.")

    normalized_entity_type = entity_type.strip().lower()

    if normalized_entity_type not in _ALLOWED_ENTITY_TYPES:
        raise ValueError(
            f"Invalid {strategy_name} entity_type "
            f"'{normalized_entity_type}'. "
            f"Allowed values: {sorted(_ALLOWED_ENTITY_TYPES)}."
        )

    return normalized_entity_type


def _validate_pcgl_variants(
    variants: list,
    *,
    entity_type: str,
) -> None:
    """
    Validate every variant selected for derived PCGL generation.
    """
    for variant in variants:
        _validate_pcgl_variant(
            variant,
            entity_type=entity_type,
        )


def _validate_pcgl_variant(
    variant: str,
    *,
    entity_type: str,
) -> None:
    """
    Validate one PCGL variant against the selected entity type.
    """
    if not isinstance(variant, str):
        raise ValueError("Each PCGL variant must be a string.")

    normalized_variant = variant.strip().upper()

    allowed_variants = (
        _ALLOWED_PCGL_VARIANTS_BY_ENTITY_TYPE[
            entity_type
        ]
    )

    if normalized_variant not in allowed_variants:
        raise ValueError(
            f"Invalid PCGL variant '{normalized_variant}' for "
            f"entity_type '{entity_type}'. "
            f"Allowed values: {sorted(allowed_variants)}."
        )


def _is_blank(value) -> bool:
    """
    Return whether a config value is missing or contains only whitespace.
    """
    return (
        value is None
        or value == ""
        or (
            isinstance(value, str)
            and value.strip() == ""
        )
    )