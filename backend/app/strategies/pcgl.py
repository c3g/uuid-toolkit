"""
Base PCGL identifier strategy.

This module validates and generates base PCGL identifiers in the format:

    <PROJECT_CODE>-<NUMERIC_ID>

Example:

    NRGI-123456

The project code contains four uppercase alphanumeric characters. It is
followed by a dash and a six-digit numeric ID.

This file only handles the base PCGL format. PCGL identifiers with variants,
such as ``NRGI-123456_EXP_0001``, are handled by
``pcgl_modifiers.py``.

How this file connects to the project
-------------------------------------
- ``registry.py`` returns ``PCGLStrategy`` when no PCGL variant is selected.
- ``pcgl_modifiers.py`` uses this strategy to validate and generate the base
  section of modified PCGL identifiers.
- The pipelines call ``validate()`` and ``generate()`` through
  ``StrategyInterface``.
- API config validation and ``registry.py`` check values such as
  ``project_code``, ``entity_type``, and selected variants before the strategy
  is used.
- ``ConfigPanel.jsx`` collects PCGL options.
- ``ToolkitPage.jsx`` builds the PCGL config sent to the backend.

Adding or changing a strategy
-----------------------------
Changes to the base PCGL format belong in this file.

To add or change a PCGL variant, update:

1. ``pcgl_modifiers.py`` with the variant behavior.
2. ``registry.py`` with the allowed entity type and variant combination.
3. ``ConfigPanel.jsx`` with the frontend option.
4. ``ToolkitPage.jsx`` if the config sent to the backend changes.
5. The related validation, generation, and pipeline tests.

A completely new identifier family should be created in its own strategy file
and registered in ``registry.py``.
"""

import random
import string

from .base import StrategyInterface


class PCGLStrategy(StrategyInterface):
    """
    Validate and generate base PCGL identifiers.

    Base format:

        <PROJECT_CODE>-<NUMERIC_ID>

    Example:

        NRGI-123456

    Variant-specific behavior is handled separately by
    ``PCGL_Modifiers``.
    """

    PROJECT_CODE_LENGTH = 4
    ID_LENGTH = 6
    EXPECTED_LENGTH = PROJECT_CODE_LENGTH + 1 + ID_LENGTH

    def validate(
        self,
        identifier: str,
        config: dict | None = None,
    ) -> dict:
        """
        Validate one base PCGL identifier.

        Validation checks:
        - The identifier is present and is a string.
        - The total length is exactly 11 characters.
        - The project code contains four uppercase alphanumeric characters.
        - A dash separates the project code from the numeric ID.
        - The numeric ID contains exactly six digits.
        - The identifier project code matches ``config["project_code"]`` when
          an expected project code is provided.

        Parameters
        ----------
        identifier:
            Identifier value to validate.

        config:
            Optional strategy configuration. ``project_code`` may be provided
            to require a specific project code.

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
        This method only checks the PCGL format and strategy config. Duplicate
        checks and database conflicts are handled later by the pipeline.
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

        if "_" in identifier:
            return {
                "valid": False,
                "error": "Invalid character",
                "message": (
                    "Base PCGL identifiers cannot contain underscores ('_')."
                ),
            }

        if len(identifier) != self.EXPECTED_LENGTH:
            return {
                "valid": False,
                "error": "Invalid length",
                "message": (
                    f"Expected identifier length of {self.EXPECTED_LENGTH}, "
                    f"but got {len(identifier)}."
                ),
            }

        project_code = identifier[:self.PROJECT_CODE_LENGTH]
        dash = identifier[self.PROJECT_CODE_LENGTH]
        id_part = identifier[self.PROJECT_CODE_LENGTH + 1:]

        config = config or {}
        expected_project = config.get("project_code")

        if dash != "-":
            return {
                "valid": False,
                "error": "Missing dash",
                "message": (
                    "Expected a dash ('-') at position "
                    f"{self.PROJECT_CODE_LENGTH}, but it was not found."
                ),
            }

        if not project_code.isalnum() or not project_code.isupper():
            return {
                "valid": False,
                "error": "Invalid project code",
                "message": (
                    "Project code must be uppercase alphanumeric, "
                    f"but got '{project_code}'."
                ),
            }

        if not id_part.isdigit():
            return {
                "valid": False,
                "error": "Invalid 6 digit ID code",
                "message": (
                    f"ID part must be numeric, but got '{id_part}'."
                ),
            }

        if expected_project is not None:
            if not isinstance(expected_project, str):
                return {
                    "valid": False,
                    "error": "Invalid config",
                    "message": (
                        "Expected project_code in config to be a string."
                    ),
                }

            if project_code != expected_project:
                return {
                    "valid": False,
                    "error": "Project code mismatch",
                    "message": (
                        f"Identifier project code '{project_code}' does not "
                        "match the expected project code "
                        f"'{expected_project}'."
                    ),
                }

        return {
            "valid": True,
            "error": None,
            "message": "Identifier is valid.",
        }

    def generate(
        self,
        config: dict | None = None,
    ) -> str:
        """
        Generate one base PCGL identifier.

        The project code comes from ``config["project_code"]``. The numeric
        section is generated as six random digits.

        Example:

            NRGI-123456

        Parameters
        ----------
        config:
            Strategy configuration containing the required ``project_code``.

        Returns
        -------
        str
            Newly generated base PCGL identifier.

        Raises
        ------
        ValueError
            Raised when ``project_code`` is missing, has the wrong type, is not
            four characters long, or is not uppercase alphanumeric.

        Notes
        -----
        This method only creates one candidate identifier. The generation
        pipeline handles duplicate checks and database conflicts.
        """
        if config is None or "project_code" not in config:
            raise ValueError(
                "Missing config for PCGL generation. "
                "'project_code' is required."
            )

        project_code = config.get("project_code")

        if not isinstance(project_code, str):
            raise ValueError("project_code must be a string.")

        if len(project_code) != self.PROJECT_CODE_LENGTH:
            raise ValueError("project_code must be 4 characters.")

        if not project_code.isalnum() or not project_code.isupper():
            raise ValueError(
                "project_code must be uppercase alphanumeric."
            )

        random_digits = random.choices(
            string.digits,
            k=self.ID_LENGTH,
        )
        random_id = "".join(random_digits)

        return f"{project_code}-{random_id}"