"""
Custom identifier strategy.

This module validates and generates identifiers using a format chosen by the
user:

    <PREFIX><CONNECTOR><SUFFIX>

Examples:

    C3G-1234567
    DONUT+568
    NRGI_909090
    ABC1239999

The prefix can either be fixed or randomly generated. The connector is
optional, and the suffix is always generated according to a selected character
type and length.

Supported character types:

- ``numeric``: digits only.
- ``letters``: letters only.
- ``alphanumeric``: letters and digits.

How this file connects to the project
-------------------------------------
- ``registry.py`` creates ``CustomStrategy`` using the config received from the
  pipeline.
- ``StrategyInterface`` defines the shared ``validate()`` and ``generate()``
  methods implemented here.
- API config validation should reject missing or invalid CUSTOM options before
  the strategy is created.
- ``ConfigPanel.jsx`` displays the CUSTOM format controls.
- ``ToolkitPage.jsx`` builds the CUSTOM config sent to the backend.
- The pipelines handle duplicate checks and database conflicts after this
  strategy validates or generates an identifier.

Changing the CUSTOM format
--------------------------
When adding a new prefix mode, connector, or character type, update:

1. The allowed values and related logic in this file.
2. API config validation.
3. The CUSTOM controls in ``ConfigPanel.jsx``.
4. ``ToolkitPage.jsx`` if the config shape changes.
5. Validation and generation tests.

A completely new identifier family should use its own strategy file and be
registered separately in ``registry.py``.
"""

import random
import string

from .base import StrategyInterface


class CustomStrategy(StrategyInterface):
    """
    Validate and generate identifiers using one custom format configuration.

    One instance stores the normalized rules for a custom format and reuses
    them for every identifier processed during the request.

    Format:

        <PREFIX><CONNECTOR><SUFFIX>

    In fixed-prefix mode, every identifier must use the same prefix. In
    random-prefix mode, the prefix is checked against the configured character
    type and length.
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
        "+",
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
        Create a custom strategy from the selected format options.

        Parameters
        ----------
        prefix_mode:
            ``"fixed"`` to reuse one exact prefix or ``"random"`` to generate
            and validate the prefix by character type and length.

        connector:
            Value placed between the prefix and suffix. Supported values are
            ``"-"``, ``"_"``, ``"+"``, and an empty string.

        suffix_type:
            Required character type for the suffix.

        suffix_length:
            Required number of characters in the suffix.

        prefix_type:
            Required character type for a random prefix.

        prefix_length:
            Required number of characters in a random prefix.

        fixed_prefix:
            Exact prefix used when ``prefix_mode`` is ``"fixed"``.

        Raises
        ------
        ValueError
            Raised when a required option is missing or invalid.

        Notes
        -----
        ``registry.py`` passes these values into the constructor. If a parameter
        or config key changes here, the registry, API config validation,
        ``ConfigPanel.jsx``, and ``ToolkitPage.jsx`` may also need updates.
        """
        self.prefix_mode = self.normalize_prefix_mode(prefix_mode)
        self.connector = self.normalize_connector(connector)

        self.suffix_type = self.normalize_char_type(
            suffix_type,
            "suffix_type",
        )
        self.suffix_length = self.normalize_length(
            suffix_length,
            "suffix_length",
        )

        if self.prefix_mode == "fixed":
            self.fixed_prefix = self.normalize_fixed_prefix(
                fixed_prefix
            )
            self.prefix_length = len(self.fixed_prefix)
            self.prefix_type = None
        else:
            self.fixed_prefix = None
            self.prefix_type = self.normalize_char_type(
                prefix_type,
                "prefix_type",
            )
            self.prefix_length = self.normalize_length(
                prefix_length,
                "prefix_length",
            )

    def validate(
        self,
        identifier: str,
        config: dict | None = None,
    ) -> dict:
        """
        Validate one identifier against the stored custom format.

        Validation checks:
        - The identifier is present and is a string.
        - The total length matches the configured format.
        - The connector appears in the expected position.
        - The prefix follows the fixed or random prefix rules.
        - The suffix matches its configured character type and length.

        Parameters
        ----------
        identifier:
            Custom identifier to validate.

        config:
            Kept for compatibility with ``StrategyInterface``. This strategy
            uses the normalized values stored during initialization.

        Returns
        -------
        dict
            Validation result using the shared strategy shape:

            {
                "valid": bool,
                "error": str | None,
                "message": str,
            }

        Notes
        -----
        File duplicates and database conflicts are handled later by the
        pipeline.
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

        prefix_result = self._validate_prefix(
            split_result["prefix"]
        )

        if prefix_result["valid"] is False:
            return prefix_result

        suffix_result = self._validate_suffix(
            split_result["suffix"]
        )

        if suffix_result["valid"] is False:
            return suffix_result

        return {
            "valid": True,
            "error": None,
            "message": "Custom identifier is valid.",
        }

    def _validate_prefix(
        self,
        prefix: str,
    ) -> dict:
        """
        Validate the prefix using the selected prefix mode.

        A fixed prefix must match exactly. A random prefix must match its
        configured character type and length.
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

        if not self._matches_type(
            prefix,
            self.prefix_type,
        ):
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

    def _validate_suffix(
        self,
        suffix: str,
    ) -> dict:
        """
        Validate the suffix character type and length.
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

        if not self._matches_type(
            suffix,
            self.suffix_type,
        ):
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

    def generate(
        self,
        config: dict | None = None,
    ) -> str:
        """
        Generate one identifier using the stored custom format.

        A fixed prefix is reused directly. A random prefix and the suffix are
        generated using their configured character types and lengths.

        Parameters
        ----------
        config:
            Kept for compatibility with ``StrategyInterface``. This strategy
            uses the normalized values stored during initialization.

        Returns
        -------
        str
            Newly generated custom identifier.

        Notes
        -----
        This method creates one candidate identifier. The generation pipeline
        checks it against uploaded and stored identifiers.
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

    def _split_identifier(
        self,
        identifier: str,
    ) -> dict:
        """
        Split an identifier into its prefix and suffix sections.

        An empty connector uses ``prefix_length`` as the split point. A
        non-empty connector must appear directly after the prefix.
        """
        if self.connector == "":
            return {
                "valid": True,
                "prefix": identifier[:self.prefix_length],
                "suffix": identifier[self.prefix_length:],
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

        return {
            "valid": True,
            "prefix": identifier[:self.prefix_length],
            "suffix": identifier[
                connector_index + len(self.connector):
            ],
        }

    def _generate_part(
        self,
        char_type: str,
        length: int,
    ) -> str:
        """
        Generate one random prefix or suffix section.
        """
        characters = self._generation_chars_for_type(
            char_type
        )

        return "".join(
            random.choices(
                characters,
                k=length,
            )
        )

    def _generation_chars_for_type(
        self,
        char_type: str,
    ) -> str:
        """
        Return the character set used for a configured character type.
        """
        if char_type == "numeric":
            return string.digits

        if char_type == "letters":
            return string.ascii_uppercase

        if char_type == "alphanumeric":
            return string.ascii_uppercase + string.digits

        raise ValueError(
            f"Unsupported character type: {char_type}"
        )

    def normalize_char_type(
        self,
        value: str,
        field_name: str,
    ) -> str:
        """
        Normalize and validate a prefix or suffix character type.
        """
        if not isinstance(value, str):
            raise ValueError(
                f"'{field_name}' must be a string."
            )

        normalized = value.strip().lower()

        if normalized not in self.ALLOWED_CHAR_TYPES:
            raise ValueError(
                f"Invalid {field_name}: '{value}'. "
                f"Allowed values: "
                f"{sorted(self.ALLOWED_CHAR_TYPES)}."
            )

        return normalized

    def normalize_length(
        self,
        value: int,
        field_name: str,
    ) -> int:
        """
        Convert a configured length to a positive integer.
        """
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

    def normalize_connector(
        self,
        value: str,
    ) -> str:
        """
        Normalize and validate the connector between the two ID sections.

        ``None`` and the string ``"none"`` are treated as no connector.
        """
        if value is None:
            value = ""

        if not isinstance(value, str):
            raise ValueError(
                "'connector' must be a string."
            )

        if value == "none":
            value = ""

        if value not in self.ALLOWED_CONNECTORS:
            raise ValueError(
                f"Invalid connector '{value}'. "
                f"Allowed values: "
                f"{sorted(self.ALLOWED_CONNECTORS)}."
            )

        return value

    def _matches_type(
        self,
        value: str,
        char_type: str,
    ) -> bool:
        """
        Check whether a value matches a configured character type.
        """
        if len(value) == 0:
            return False

        if char_type == "numeric":
            return value.isdigit()

        if char_type == "letters":
            return value.isalpha()

        if char_type == "alphanumeric":
            return value.isalnum()

        return False

    def normalize_fixed_prefix(
        self,
        value: str | None,
    ) -> str:
        """
        Normalize and validate the prefix used in fixed-prefix mode.
        """
        if value is None:
            raise ValueError(
                "'fixed_prefix' is required when "
                "prefix_mode is 'fixed'."
            )

        if not isinstance(value, str):
            raise ValueError(
                "'fixed_prefix' must be a string."
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

    def normalize_prefix_mode(
        self,
        value: str,
    ) -> str:
        """
        Normalize and validate the selected prefix mode.
        """
        if not isinstance(value, str):
            raise ValueError(
                "'prefix_mode' must be a string."
            )

        normalized = value.strip().lower()

        if normalized not in self.ALLOWED_PREFIX_MODES:
            raise ValueError(
                f"Invalid prefix mode: '{value}'. "
                f"Allowed values: "
                f"{sorted(self.ALLOWED_PREFIX_MODES)}."
            )

        return normalized