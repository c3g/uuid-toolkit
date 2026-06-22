"""
Custom strategy for identifiers that implements the strategy interface.

This module defines the validation and generation logic for custom identifiers.
A user can customize three components of the ID, the prefix, connector, and the suffix.
The identifiers would follow the following format:

    <PREFIX><CONNECTOR><SUFFIX>

    Examples:

        C3G-1234567

        DONUT+568

        NRGI_909090

The user can indicate the length of the prefix and suffix as well as the type.
For the type they can choose between alphanumeric, numeric and letters.
For connectors they can choose a dash -, underscore _ , or a plus +.

Based on the user requirements, the IDs can be validated against the restrictions provided or be generated to follow the instructions.
This file also validates and generates ID based on the already-normalized values in config passed from registry.py
It would require prefix_mode, connector, suffix_type, and suffix_length.
Depending on the prefix_mode it would require prefix_type, prefix_length, or fixed_prefix.

Dependency notes:
- ConfigPanel.jsx decides what custom options the user can choose from in the frontend
- App.jsx buildConfig() must build the config dict with all the appropriate fields required
- api/utils also validates the config and the fields within to ensure they are within acceptable ranges and types.
- pipeline.py calls validate() and generate() through StrategyInterface so the return formats should stay consistent to ensure pipeline working properly.

"""
from .base import StrategyInterface
import random
import string

class CustomStrategy(StrategyInterface):
    """
    Strategy for validating and generating custom user defined identifiers

    This class implements the StrategyInterface used by the pipeline.
    It only handles the custom format from the users and shouldn't be used for the CPHI project or other ones.
    """
    ALLOWED_PREFIX_MODES = {
        "random",
        "fixed",
    }
    ALLOWED_CHAR_TYPES = {
        "alphanumeric",
        "numeric",
        "letters",
    }
    ALLOWED_CONNECTORS = {
        "-",
        "_",
        "",
        "+"
    }
    
    def __init__(
        self,
        prefix_mode: str,
        connector: str,
        suffix_type: str,
        suffix_length: int,
        prefix_type: str | None = None,
        prefix_length: int | None = None,
        fixed_prefix: str | None = None,
    ):
        self.prefix_mode = self.normalize_prefix_mode(prefix_mode)
        self.connector = self.normalize_connector(connector)

        self.suffix_type = self.normalize_char_type(suffix_type, "suffix_type")
        self.suffix_length = self.normalize_length(suffix_length, "suffix_length")

        if self.prefix_mode == "fixed":
            self.fixed_prefix = self.normalize_fixed_prefix(fixed_prefix)
            self.prefix_length = len(self.fixed_prefix)
            self.prefix_type = None

        else:
            self.fixed_prefix = None
            self.prefix_type = self.normalize_char_type(prefix_type, "prefix_type")
            self.prefix_length = self.normalize_length(prefix_length, "prefix_length")
    
    def validate(self, identifier: str, config: dict|None = None) -> dict:
        if identifier is None:
            return {
                "valid": False,
                "error": "Missing identifier",
                "message": "Identifier not present.",
            }

        if not isinstance(identifier, str):
            return {
                "valid": False,
                "error": "Invalid type",
                "message": (
                    "Expected a string identifier, "
                    f"but got {type(identifier).__name__}."
                ),
            }

        expected_length = (
            self.prefix_length
            + len(self.connector)
            + self.suffix_length
        )

        if len(identifier) != expected_length:
            return {
                "valid": False,
                "error": "Invalid length",
                "message": (
                    f"Expected identifier length of {expected_length}, "
                    f"but got {len(identifier)}."
                ),
            }

        split_result = self._split_identifier(identifier)

        if split_result["valid"] is False:
            return split_result

        prefix = split_result["prefix"]
        suffix = split_result["suffix"]

        prefix_result = self._validate_prefix(prefix)

        if prefix_result["valid"] is False:
            return prefix_result

        suffix_result = self._validate_suffix(suffix)

        if suffix_result["valid"] is False:
            return suffix_result

        return {
            "valid": True,
            "error": None,
            "message": "Custom identifier is valid.",
        }
    
    def _validate_prefix(self, prefix: str) -> dict:
        if len(prefix) != self.prefix_length:
            return {
                "valid": False,
                "error": "Invalid prefix length",
                "message": (
                    f"Expected prefix length {self.prefix_length}, "
                    f"but got {len(prefix)}."
                ),
            }

        if self.prefix_mode == "fixed":
            if prefix != self.fixed_prefix:
                return {
                    "valid": False,
                    "error": "Invalid fixed prefix",
                    "message": (
                        f"Expected fixed prefix '{self.fixed_prefix}', "
                        f"but got '{prefix}'."
                    ),
                }

            return {
                "valid": True,
                "error": None,
                "message": "Fixed prefix is valid.",
            }

        if not self._matches_type(prefix, self.prefix_type):
            return {
                "valid": False,
                "error": "Invalid prefix",
                "message": (
                    f"Prefix must be {self.prefix_type} "
                    f"with length {self.prefix_length}."
                ),
            }

        return {
            "valid": True,
            "error": None,
            "message": "Prefix is valid.",
        }

    def _validate_suffix(self,suffix: str) -> dict:
        if len(suffix) != self.suffix_length:
            return {
                "valid": False,
                "error": "Invalid suffix length",
                "message": (
                    f"Expected suffix length {self.suffix_length}, "
                    f"but got {len(suffix)}."
                ),
            }

        if not self._matches_type(suffix, self.suffix_type):
            return {
                "valid": False,
                "error": "Invalid suffix",
                "message": (
                    f"Suffix must be {self.suffix_type} "
                    f"with length {self.suffix_length}."
                ),
            }

        return {
            "valid": True,
            "error": None,
            "message": "Suffix is valid.",
        }

    
    def generate(self, config: dict | None = None) -> str:
        if self.prefix_mode == "fixed":
            prefix = self.fixed_prefix
        else:
            prefix = self._generate_part(
                self.prefix_type,
                self.prefix_length,
            )

        suffix = self._generate_part(
            self.suffix_type,
            self.suffix_length,
        )

        return f"{prefix}{self.connector}{suffix}"

    def _split_identifier(self, identifier: str) -> dict:
        if self.connector == "":
            prefix = identifier[:self.prefix_length]
            suffix = identifier[self.prefix_length:]

            return {
                "valid": True,
                "prefix": prefix,
                "suffix": suffix,
            }

        connector_index = self.prefix_length

        actual_connector = identifier[connector_index]

        if actual_connector != self.connector:
            return {
                "valid": False,
                "error": "Invalid connector",
                "message": (
                    f"Expected connector '{self.connector}' "
                    f"at position {connector_index}."
                ),
            }

        prefix = identifier[:self.prefix_length]
        suffix = identifier[connector_index + len(self.connector):]

        return {
            "valid": True,
            "prefix": prefix,
            "suffix": suffix,
        }

    def _generate_part(self, char_type: str, length: int) -> str:
        chars = self._generation_chars_for_type(char_type)
        return "".join(random.choices(chars, k=length))

    def _generation_chars_for_type(self, char_type: str) -> str:
        if char_type == "numeric":
            return string.digits

        if char_type == "letters":
            return string.ascii_uppercase

        if char_type == "alphanumeric":
            return string.ascii_uppercase + string.digits

        raise ValueError(f"Unsupported character type: {char_type}")

    def normalize_char_type(self, value:str, field_name: str) -> str:
        if not isinstance(value,str):
            raise ValueError(f"'{field_name}' provided must be a string")
        normalized = value.strip().lower()

        if normalized not in self.ALLOWED_CHAR_TYPES:
            raise ValueError(
                f"Invalid {field_name}: '{value}'"
                f"Allowed values: '{self.ALLOWED_CHAR_TYPES}'"
            )
        return normalized
    def normalize_length(self, value: int, field_name:str) -> int:
        try:
            normalized = int(value)
        except (TypeError,ValueError):
            raise ValueError(f"'{field_name}' provided must be an integer.")
        
        if normalized <=0:
            raise ValueError(f"'{field_name}' must be greater than 0.")
        #Can add another check to limit the size of the int if needed
        return normalized
    def normalize_connector(self, value:str)->str:
        if value is None:
            value =""
        if not isinstance(value,str):
            raise ValueError(f"'Connector' has to be a string")
        if value == "none":
            value = ""
        if value not in self.ALLOWED_CONNECTORS:
            raise ValueError(
                f"Invaldi connector '{value}'. Allowed values are '{self.ALLOWED_CONNECTORS}' or empty."
            )
        return value
    def _matches_type(self, value: str, char_type: str) -> bool:
        if len(value) == 0:
            return False

        if char_type == "numeric":
            return value.isdigit()

        if char_type == "letters":
            return value.isalpha()

        if char_type == "alphanumeric":
            return value.isalnum()

        return False
    def normalize_fixed_prefix(self, value:str |None) -> str:
        if value is None:
            raise ValueError(
                f"'fixe_prefix' is required when prefix_mode is 'fixed'"
            )
        if not isinstance(value, str):
            raise ValueError("'fixed_prefix' must be a string.")
        fixed_prefix = value.strip()
        
        if fixed_prefix == "":
            raise ValueError("'fixed_prefix' cannot be empty.")

        if not fixed_prefix.isalnum():
            raise ValueError(
                "'fixed_prefix' must contain only letters and numbers."
            )
        return fixed_prefix
    def normalize_prefix_mode(self, value: str) -> str:
        if not isinstance(value,str):
            raise ValueError(
                "'prefix_mode' must be a string."
            )
        normalized = value.strip().lower()

        if normalized not in self.ALLOWED_PREFIX_MODES:
            raise ValueError(
                f"Invalide prefix mode: {value}"
                f"Allowed values: {sorted(self.ALLOWED_PREFIX_MODES)}."
            )
        return normalized