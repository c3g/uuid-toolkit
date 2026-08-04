"""
Base CPHI identifier strategy.

This module validates and generates base CPHI identifiers in the format:

    <PROJECT_CODE>-<NUMERIC_ID>

Example:

    NRGI-123456

The project code must contain four uppercase alphanumeric characters, followed
by a dash and a six-digit numeric ID. When ``project_code`` is provided in the
config, validation also checks that it matches the identifier.

CPHI identifiers in this toolkit do not include variant or modifier sections.
Identifiers with variants such as ``_EXP_`` or ``_SPE_`` belong to the PCGL
strategy and are handled by ``pcgl_modifiers.py``.

How this file connects to the project
-------------------------------------
- ``registry.py`` returns ``CPHIStrategy`` when the selected CPHI format does
  not require a modifier strategy.
- The validation and generation pipelines call ``validate()`` and
  ``generate()`` through ``StrategyInterface``.
- API config validation should check and normalize values such as
  ``project_code`` and ``entity_type`` before the strategy is created.
- ``ConfigPanel.jsx`` collects CPHI options, while ``ToolkitPage.jsx`` builds
  the config sent to the backend.

Adding or changing a strategy
-----------------------------
A completely new identifier family should be created in its own strategy file
and registered in ``registry.py``. Its backend config validation, frontend
selector option, frontend controls, and ``ToolkitPage.jsx`` config builder must
also be updated.

This file normally only changes when the rules for base CPHI identifiers
change. CPHI modifier rules belong in ``cphi_modifiers.py``.
"""

import random
import string

from .base import StrategyInterface


class CPHIStrategy(StrategyInterface):
    """
    Validate and generate base CPHI identifiers.

    Base format:

        <PROJECT_CODE>-<NUMERIC_ID>

    Example:

        NRGI-123456

    This class contains the complete CPHI strategy used by the toolkit.
    Variant and modifier identifiers belong to the PCGL strategy.
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
        Validate one base CPHI identifier.

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
        This method only checks CPHI format and config rules. File duplicates
        and database conflicts are handled later by the pipeline.
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
                    "Base CPHI identifiers cannot contain underscores ('_')."
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
        Generate one base CPHI identifier.

        The project code comes from ``config["project_code"]`` and the numeric
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
            Newly generated base CPHI identifier.

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
                "Missing config for CPHI generation. "
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