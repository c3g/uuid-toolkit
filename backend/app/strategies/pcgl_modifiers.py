"""
PCGL modifier strategy.

This file handles PCGL identifiers that extend an existing base PCGL ID with
one or more selected variants.

Modified PCGL format:

    <BASE_PCGL>_<VARIANT>_<4_DIGIT_ID>

Example:

    NRGI-123456_EXP_4829

There are two generation workflows:

- A singular ``variant`` generates one complete modified PCGL identifier.
- A plural ``variants`` list derives several identifiers from one existing
  base PCGL identifier.

How this file connects to the project
-------------------------------------
- ``registry.py`` returns ``PCGL_Modifiers`` when ``variant`` or ``variants``
  are included in the PCGL config.
- ``pcgl.py`` validates and generates the base PCGL section.
- ``base.py`` defines the shared strategy methods used here.
- The generation pipeline checks ``get_strategy_info()`` to choose between
  normal fill-missing generation and derived generation.
- ``ConfigPanel.jsx`` controls which variants the user can select.
- ``ToolkitPage.jsx`` sends either ``variant`` or ``variants`` to the backend.
- File duplicates and database conflicts are checked by the pipeline after an
  identifier is generated.

Adding a PCGL variant
---------------------
1. Add the abbreviation to ``ALLOWED_VARIANTS`` in this file.
2. Add it to the correct entity type in
   ``_ALLOWED_PCGL_VARIANTS_BY_ENTITY_TYPE`` inside ``registry.py``.
3. Add the option to the PCGL controls in ``ConfigPanel.jsx``.
4. Make sure ``ToolkitPage.jsx`` sends the abbreviation without underscores.
5. Add validation, single-generation, and derived-generation tests.

A completely new identifier family should use its own strategy file and be
registered separately in ``registry.py``.
"""

import random
import string

from .base import StrategyInterface
from .pcgl import PCGLStrategy


class PCGL_Modifiers(StrategyInterface):
    """
    Validate and generate PCGL identifiers that contain variants.

    ``PCGLStrategy`` handles the base identifier. This class handles the
    variant marker, the four-digit modifier ID, and the derived-generation
    workflow used when several variants are selected.
    """

    MODIFIER_ID_LENGTH = 4

    ALLOWED_VARIANTS = {
        "SPE",
        "EXP",
        "LIB",
        "RG",
        "WRK",
        "ANA",
    }

    def __init__(self):
        """
        Create the base PCGL strategy used for shared base-ID checks.
        """
        self.base_strategy = PCGLStrategy()

    def validate(
        self,
        identifier: str,
        config: dict | None = None,
    ) -> dict:
        """
        Validate one modified PCGL identifier.

        Expected format:

            <BASE_PCGL>_<VARIANT>_<4_DIGIT_ID>

        Example:

            NRGI-123456_EXP_4829

        Validation checks:
        - ``config["variant"]`` is present and supported.
        - The identifier is present and is a string.
        - The expected variant marker appears in the identifier.
        - The base section passes ``PCGLStrategy.validate()``.
        - The modifier ID contains exactly four numeric digits.

        Parameters
        ----------
        identifier:
            Modified PCGL identifier to validate.

        config:
            Strategy configuration containing ``variant`` and any values used
            by the base PCGL strategy, such as ``project_code``.

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
        ``registry.py`` checks whether the variant is allowed for the selected
        entity type. This method checks whether the identifier matches the
        specific variant passed in the config.
        """
        config = config or {}
        variant = config.get("variant")

        if variant is None:
            return {
                "valid": False,
                "error": "Missing variant",
                "message": (
                    "Missing 'variant' in config for "
                    "PCGL modifier validation."
                ),
            }

        if variant not in self.ALLOWED_VARIANTS:
            return {
                "valid": False,
                "error": "Invalid variant",
                "message": (
                    f"Variant must be one of "
                    f"{sorted(self.ALLOWED_VARIANTS)}."
                ),
            }

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

        expected_marker = f"_{variant}_"

        if expected_marker not in identifier:
            return {
                "valid": False,
                "error": "Missing variant marker",
                "message": (
                    f"Expected variant marker '{expected_marker}' "
                    "in identifier."
                ),
            }

        base_id, modifier_id = identifier.split(
            expected_marker,
            1,
        )

        # Reuse the base strategy so the base PCGL rules stay in one place.
        base_result = self.base_strategy.validate(
            base_id,
            config,
        )

        if not base_result["valid"]:
            return base_result

        if len(modifier_id) != self.MODIFIER_ID_LENGTH:
            return {
                "valid": False,
                "error": "Invalid modifier ID length",
                "message": (
                    "Modifier ID must be "
                    f"{self.MODIFIER_ID_LENGTH} digits long."
                ),
            }

        if not modifier_id.isdigit():
            return {
                "valid": False,
                "error": "Invalid modifier ID",
                "message": "Modifier ID must be numeric.",
            }

        return {
            "valid": True,
            "error": None,
            "message": "Modified PCGL identifier is valid.",
        }

    def generate(
        self,
        config: dict | None = None,
    ) -> str:
        """
        Generate one modified PCGL identifier.

        This method is used when the config contains one singular ``variant``.
        It first generates a base PCGL ID, then adds the selected variant and a
        random four-digit modifier ID.

        Example:

            NRGI-123456_EXP_4829

        Parameters
        ----------
        config:
            Strategy configuration containing ``variant`` and the values
            required by ``PCGLStrategy.generate()``, including
            ``project_code``.

        Returns
        -------
        str
            Newly generated modified PCGL identifier.

        Raises
        ------
        ValueError
            Raised when the variant is missing or unsupported, or when the
            base PCGL configuration is invalid.

        Notes
        -----
        The frontend sends the variant abbreviation without underscores.
        This method adds the separators when it builds the identifier.
        """
        config = config or {}
        variant = config.get("variant")

        if variant is None:
            raise ValueError(
                "Missing 'variant' in config for "
                "PCGL modifier generation."
            )

        if variant not in self.ALLOWED_VARIANTS:
            raise ValueError(
                f"Invalid variant '{variant}'. "
                f"Allowed values: {sorted(self.ALLOWED_VARIANTS)}."
            )

        base_id = self.base_strategy.generate(config)

        modifier_id = "".join(
            random.choices(
                string.digits,
                k=self.MODIFIER_ID_LENGTH,
            )
        )

        return f"{base_id}_{variant}_{modifier_id}"

    def get_strategy_info(
        self,
        config: dict | None = None,
    ) -> dict:
        """
        Tell the generation pipeline which PCGL workflow to use.

        A non-empty ``variants`` list means the user wants several identifiers
        derived from an existing base PCGL ID. In that case, the pipeline must
        preserve the source identifier and write each variant into a separate
        output column.

        A singular ``variant`` uses the normal fill-missing workflow inherited
        from ``StrategyInterface``.

        Parameters
        ----------
        config:
            PCGL configuration containing an optional ``variants`` list.

        Returns
        -------
        dict
            Derived-generation metadata when ``variants`` is present.
            Otherwise, the default strategy metadata from ``base.py``.
        """
        config = config or {}

        if config.get("variants"):
            return {
                "generation_mode": "derive_from_existing",
                "output_mode": "multiple_columns",
                "requires_existing_identifier": True,
                "preserve_input_identifier": True,
            }

        return super().get_strategy_info(config)

    def generate_derived_identifiers(
        self,
        source_identifier: str,
        config: dict | None = None,
    ) -> dict[str, str]:
        """
        Generate several PCGL variants from one existing base PCGL ID.

        Example input:

            source_identifier = "NRGI-123456"

            config = {
                "project_code": "NRGI",
                "entity_type": "sample",
                "variants": ["EXP", "LIB"],
            }

        Example result:

            {
                "EXP": "NRGI-123456_EXP_4829",
                "LIB": "NRGI-123456_LIB_1038",
            }

        Parameters
        ----------
        source_identifier:
            Existing base PCGL identifier used to build each derived value.

        config:
            Strategy configuration containing a non-empty ``variants`` list
            and any values needed to validate the base identifier.

        Returns
        -------
        dict[str, str]
            Mapping from each selected variant to its generated identifier.

        Raises
        ------
        ValueError
            Raised when no variants are provided, the source identifier is not
            a valid base PCGL ID, or a selected variant is unsupported.

        Notes
        -----
        This method generates candidate values only. The pipeline decides the
        final output-column names and checks the generated identifiers for
        file-level and database-level conflicts.
        """
        config = config or {}
        variants = config.get("variants", [])

        if not variants:
            raise ValueError(
                "Missing 'variants' for PCGL derived generation."
            )

        # Derived values can only be created from a valid base PCGL identifier.
        base_result = self.base_strategy.validate(
            source_identifier,
            config,
        )

        if base_result["valid"] is not True:
            raise ValueError(base_result["message"])

        generated_outputs: dict[str, str] = {}

        for variant in variants:
            if variant not in self.ALLOWED_VARIANTS:
                raise ValueError(
                    f"Invalid variant '{variant}'. "
                    f"Allowed values: {sorted(self.ALLOWED_VARIANTS)}."
                )

            modifier_id = "".join(
                random.choices(
                    string.digits,
                    k=self.MODIFIER_ID_LENGTH,
                )
            )

            generated_outputs[variant] = (
                f"{source_identifier}_{variant}_{modifier_id}"
            )

        return generated_outputs