#The purpose of the registry is to record all the different types of identifiers
#It will help with choosing the strategy for validation 

from .uuid_standard import UUIDStrategy
from .cphi import CPHIStrategy
from .cphi_modifiers import CPHI_Modifiers
from .base import StrategyInterface
from .custom import CustomStrategy


_ALLOWED_CPHI_VARIANTS_BY_ENTITY_TYPE = {
    "patient": {"SPE"},
    "sample": {"EXP", "RG", "ANA", "LIB", "WRK"},
}
_ALLOWED_UUID_VERSIONS = {4}  # Extend this set as more versions are supported

def get_strategy(
    strategy_name: str,
    config: dict | None = None
) -> StrategyInterface:
    """
    Build and return a fully configured identifier strategy.

    Parameters
    ----------
    strategy_name : str
        Identifier family: 'UUID' or 'CPHI'

    config : dict | None
        Optional configuration:
        - UUID:
            { "version": 4 }
        - CPHI:
            {
                "project_code": "NRGI",   # optional for validation
                "variant": "EXP"          # optional
            }
    """
    config = config or {}
    strategy_name = strategy_name.strip().upper()

    # UUID family
    
    if strategy_name == "UUID":
        return get_uuid_strategy(config)
    

    #CPHI family
    elif strategy_name == "CPHI":

        
        return get_cphi_strategy(config)
    elif strategy_name == "CUSTOM":
        return get_custom_strategy(config)
    #unkown strategy
    else:
        raise ValueError(
            f"Strategy name '{strategy_name}' was not found in the registry."
        )
    
def get_uuid_strategy(config:dict)->StrategyInterface:
    if "version" not in config:
        raise ValueError("Missing verion in config file.")
    version = config["version"]
    if version not in _ALLOWED_UUID_VERSIONS:
        raise ValueError(f"The version provided: {version} is not allowed, please choose from from {config[version]}.")
    return UUIDStrategy()
def get_cphi_strategy(config: dict) -> StrategyInterface:
    """
    Choose either base CPHI or modified CPHI strategy.

    CPHI IDs must always belong to either:
    - patient
    - sample

    Variant is optional.
    """

    project_code = config.get("project_code")
    entity_type = config.get("entity_type")
    variant = config.get("variant")

    if _is_blank(project_code):
        raise ValueError("Missing 'project_code' in config for CPHI strategy.")

    if not isinstance(project_code, str):
        raise ValueError("'project_code' must be a string.")

    if _is_blank(entity_type):
        raise ValueError(
            "Missing 'entity_type' in config for CPHI strategy. "
            "Expected 'patient' or 'sample'."
        )

    if not isinstance(entity_type, str):
        raise ValueError("'entity_type' must be a string.")

    entity_type = entity_type.strip().lower()

    if entity_type not in _ALLOWED_CPHI_VARIANTS_BY_ENTITY_TYPE:
        raise ValueError(
            f"Invalid CPHI entity_type '{entity_type}'. "
            f"Allowed values: {sorted(_ALLOWED_CPHI_VARIANTS_BY_ENTITY_TYPE)}."
        )

    # No variant means base CPHI format:
    # NRGI-123456
    if _is_blank(variant):
        return CPHIStrategy()

    if not isinstance(variant, str):
        raise ValueError("'variant' must be a string.")

    variant = variant.strip().upper()

    allowed_variants = _ALLOWED_CPHI_VARIANTS_BY_ENTITY_TYPE[entity_type]

    if variant not in allowed_variants:
        raise ValueError(
            f"Invalid CPHI variant '{variant}' for entity_type '{entity_type}'. "
            f"Allowed values: {sorted(allowed_variants)}."
        )

    # Variant exists, so use modified CPHI format:
    # NRGI-123456_EXP_0001
    return CPHI_Modifiers()


def _is_blank(value) -> bool:
    return value is None or value == "" or (isinstance(value, str) and value.strip() == "")

def get_custom_strategy(config: dict) -> StrategyInterface:
    config = config or {}

    prefix_mode = config.get("prefix_mode", "random")
    connector = config.get("connector", "")

    suffix_type = config.get("suffix_type")
    suffix_length = config.get("suffix_length")

    if prefix_mode == "fixed":
        return CustomStrategy(
            prefix_mode=prefix_mode,
            fixed_prefix=config.get("fixed_prefix"),
            connector=connector,
            suffix_type=suffix_type,
            suffix_length=suffix_length,
        )

    return CustomStrategy(
        prefix_mode=prefix_mode,
        prefix_type=config.get("prefix_type"),
        prefix_length=config.get("prefix_length"),
        connector=connector,
        suffix_type=suffix_type,
        suffix_length=suffix_length,
    )