"""
Custom identifier strategy.

This module defines validation and generation logic for user-defined custom
identifiers. A custom identifier is built from three configurable sections:

    <PREFIX><CONNECTOR><SUFFIX>

Examples:

    C3G-1234567
    DONUT+568
    NRGI_909090
    ABC1239999

The user can configure:
- prefix_mode:
    - "fixed": every ID must use the same fixed prefix.
    - "random": the prefix is generated or validated using a type and length.
- prefix_type:
    - Character type for random prefixes.
    - Only required when prefix_mode is "random".
- prefix_length:
    - Length of the random prefix.
    - Only required when prefix_mode is "random".
- fixed_prefix:
    - Exact prefix used for every ID.
    - Only required when prefix_mode is "fixed".
- connector:
    - String placed between prefix and suffix.
    - Supported values: "-", "_", "+", or "" for no connector.
- suffix_type:
    - Character type for the suffix.
- suffix_length:
    - Length of the suffix.

Supported character types:
- "numeric": digits only.
- "letters": letters only.
- "alphanumeric": letters and digits.

This strategy validates and generates IDs using normalized configuration values
passed in by registry.py. The pipeline does not need to know the custom-format
details. It only calls validate() and generate() through StrategyInterface.

Dependency notes:
- ConfigPanel.jsx controls which CUSTOM options the user can select.
- App.jsx buildConfig() must send config keys matching this strategy.
- api/utils.py should validate the same CUSTOM config keys before registry.py
  creates this strategy.
- registry.py constructs CustomStrategy from the validated config.
- pipeline.py calls validate() and generate() through StrategyInterface, so the
  validate() return shape should stay consistent with other strategies.
"""
from .base import StrategyInterface
import random
import string

class CustomStrategy(StrategyInterface):
    """
    Strategy for validating and generating user-defined custom identifiers.

    One CustomStrategy instance represents one custom ID configuration selected
    by the user. The strategy stores normalized config values on the object
    during initialization, then uses those values later during validation and
    generation.

    Custom identifier format:

        <PREFIX><CONNECTOR><SUFFIX>

    Example:

        C3G-123456

    Prefix behavior:
    - fixed mode:
        The prefix must exactly match fixed_prefix.
    - random mode:
        The prefix must match prefix_type and prefix_length.

    Suffix behavior:
    - The suffix must always match suffix_type and suffix_length.

    This class should only handle the CUSTOM strategy. CPHI, CPHI modifiers,
    UUID, and future strategies should be handled by separate strategy classes.
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
        """
        Create a CustomStrategy from user-provided config values.

        The constructor does not validate or generate an identifier directly.
        Instead, it prepares the strategy rules that validate() and generate()
        will use later.

        Parameters
        ----------
        prefix_mode:
            Determines how the prefix is handled. Supported values are
            "fixed" and "random".

        connector:
            String placed between the prefix and suffix. Supported values are
            "-", "_", "+", or "" for no connector.

        suffix_type:
            Character type required for the suffix. Supported values are
            "numeric", "letters", and "alphanumeric".

        suffix_length:
            Number of characters required in the suffix.

        prefix_type:
            Character type required for the prefix when prefix_mode is
            "random". Supported values are "numeric", "letters", and
            "alphanumeric".

        prefix_length:
            Number of characters required in the prefix when prefix_mode is
            "random".

        fixed_prefix:
            Exact prefix required when prefix_mode is "fixed". This value is
            reused during generation and checked exactly during validation.

        Behavior
        --------
        - Normalizes prefix_mode, connector, suffix_type, and suffix_length.
        - If prefix_mode is "fixed", normalizes fixed_prefix and calculates
          prefix_length from the fixed prefix.
        - If prefix_mode is "random", normalizes prefix_type and prefix_length.
        - Stores normalized values on self for validate() and generate().

        Raises
        ------
        ValueError
            Raised when required config values are missing, have the wrong type,
            or are outside the allowed options.

        Dependency notes
        ----------------
        registry.py passes values into this constructor. If constructor
        parameters or expected config key names change, update registry.py,
        api/utils.py, App.jsx buildConfig(), and ConfigPanel.jsx.

        """
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
        """
        Validate an existing custom identifier.

        The identifier is validated against the normalized rules stored on this
        CustomStrategy instance.

        Expected format:

            <PREFIX><CONNECTOR><SUFFIX>

        Validation flow:
        1. Check that the identifier is present.
        2. Check that the identifier is a string.
        3. Check the total expected length.
        4. Split the identifier into prefix and suffix sections.
        5. Validate the prefix against fixed or random prefix rules.
        6. Validate the suffix against suffix type and length rules.
        7. Return the shared validation result dictionary.

        Parameters
        ----------
        identifier:
            Identifier value to validate.

        config:
            Optional config argument kept for StrategyInterface compatibility.
            This strategy mainly uses the normalized config values stored on
            self during __init__.

        Returns
        -------
        dict
            Validation result with the shared strategy response shape:

            {
                "valid": bool,
                "error": str | None,
                "message": str
            }

        Dependency notes
        ----------------
        pipeline.py expects validate() to return the same shape across all
        strategies. If this return shape changes, pipeline.py and frontend
        result display components may also need updates.
        """
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
        """
        Validate the prefix section of a custom identifier.

        Prefix validation depends on prefix_mode:
        - fixed mode:
            The prefix must exactly match self.fixed_prefix.
        - random mode:
            The prefix must match self.prefix_type and self.prefix_length.

        Parameters
        ----------
        prefix:
            Prefix section extracted from the full identifier.

        Returns
        -------
        dict
            Validation-style result containing valid, error, and message keys.
        """
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
        """
        Validate the suffix section of a custom identifier.

        The suffix must match the configured suffix length and character type.

        Parameters
        ----------
        suffix:
            Suffix section extracted from the full identifier.

        Returns
        -------
        dict
            Validation-style result containing valid, error, and message keys.
        """
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
        """
        Generate one new custom identifier.

        Generation uses the normalized rules stored on this CustomStrategy
        instance.

        Generation flow:
        1. Use fixed_prefix if prefix_mode is "fixed".
        2. Generate a random prefix if prefix_mode is "random".
        3. Generate a suffix based on suffix_type and suffix_length.
        4. Join prefix, connector, and suffix into one identifier string.

        Parameters
        ----------
        config:
            Optional config argument kept for StrategyInterface compatibility.
            This strategy mainly uses the normalized config values stored on
            self during __init__.

        Returns
        -------
        str
            Newly generated custom identifier.

        Dependency notes
        ----------------
        This method only generates one identifier. It does not check whether
        the generated identifier is unique across the uploaded file or database.
        The generation pipeline handles conflict detection and regeneration.
        """
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
        """
        Split a full custom identifier into prefix and suffix sections.

        If the connector is empty, the identifier is split using prefix_length.
        If the connector is not empty, the method verifies that the connector
        appears at the expected position before splitting.

        Parameters
        ----------
        identifier:
            Full identifier string to split.

        Returns
        -------
        dict
            If the split is successful:

            {
                "valid": True,
                "prefix": str,
                "suffix": str
            }

            If the connector is invalid:

            {
                "valid": False,
                "error": str,
                "message": str
            }
        """
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