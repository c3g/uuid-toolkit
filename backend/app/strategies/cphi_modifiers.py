from .base import StrategyInterface
from .cphi import CPHIStrategy
import random
import string


class CPHI_Modifiers(StrategyInterface):
    MODIFIER_ID_LENGTH = 4
    ALLOWED_VARIANTS = {"SPE", "EXP", "LIB", "RG", "WRK", "ANA"}

    def __init__(self):
        self.base_strategy = CPHIStrategy()

    def validate(self, identifier: str, config: dict | None = None) -> dict:
        """
        
        """
        config = config or {}

        variant = config.get("variant")

        

        if variant is None:
            return {
                "valid": False,
                "error": "Missing variant",
                "message": "Missing 'variant' in config for CPHI modifier validation."
            }

        if variant not in self.ALLOWED_VARIANTS:
            return {
                "valid": False,
                "error": "Invalid variant",
                "message": f"Variant must be one of {sorted(self.ALLOWED_VARIANTS)}."
            }

        if identifier is None:
            return {
                "valid": False,
                "error": "Missing identifier",
                "message": "Identifier not present."
            }

        if not isinstance(identifier, str):
            return {
                "valid": False,
                "error": "Invalid type",
                "message": f"Expected a string identifier, but got {type(identifier).__name__}."
            }

        expected_marker = f"_{variant}_"

        if expected_marker not in identifier:
            return {
                "valid": False,
                "error": "Missing variant marker",
                "message": f"Expected variant marker '{expected_marker}' in identifier."
            }

        base_id, modifier_id = identifier.split(expected_marker, 1)

        base_result = self.base_strategy.validate(base_id, config)

        if not base_result["valid"]:
            return base_result

        if len(modifier_id) != self.MODIFIER_ID_LENGTH:
            return {
                "valid": False,
                "error": "Invalid modifier ID length",
                "message": f"Modifier ID must be {self.MODIFIER_ID_LENGTH} digits long."
            }

        if not modifier_id.isdigit():
            return {
                "valid": False,
                "error": "Invalid modifier ID",
                "message": "Modifier ID must be numeric."
            }
        return {
            "valid": True,
            "error": None,
            "message": "Modified CPHI identifier is valid."
        }

    def generate(self, config: dict | None = None) -> str:
        config = config or {}

        variant = config.get("variant")

        if variant is None:
            raise ValueError("Missing 'variant' in config for CPHI modifier generation.")

        if variant not in self.ALLOWED_VARIANTS:
            raise ValueError(
                f"Invalid variant '{variant}'. Allowed values: {sorted(self.ALLOWED_VARIANTS)}."
            )

        base_id = self.base_strategy.generate(config)

        modifier_id = "".join(
            random.choices(string.digits, k=self.MODIFIER_ID_LENGTH)
        )

        return f"{base_id}_{variant}_{modifier_id}"