"""
Base CPHI identifier strategy.

This module defines the validation and generation logic for the base CPHI identifiers.
A base CPHI identifier has the following format:

        <PROJECT_CODE>-<NUMERIC_ID>

        The project code is a UPPER case 4 letter string
        The numeric ID is a 6 digit numerical integer
        They are both connected by a dash (-)
    
    Example:

        NRGI-123456
Rules that have to be enforced for this strategy:
- The project code is 4 uppercase letter string
- The project code must be immediately followed by a dash
- The ID section must be 6 numeric digits
- config["project_code"] must be provided, the identifier project code must match the provided project code

This module only handles base CPHI identifiers. CPHI identifiers with varitans such as specimen (SPE) or experiments (EXP) IDs, are handled by cphi_modifiers.py.

Dependency notes:
- registry.py decides when to use CPHI strategy
- apie/utils.py should validate the CPHI relevant config values before this strategy is used to ensure that all values are normalized.
- pipeline.py calls validate() and generate() through the shared strategy interface, so the return shape of validate() and generate() should stay consisten with other strategies.
"""


from .base import StrategyInterface
import string
import random

class CPHIStrategy(StrategyInterface):
    """
    Strategy for base CPHI identifier validation and generation.

    This class implements the shared StrategyInterface used by the pipeline.
    It only handles base CPHI IDs, not variant-based CPHI modifier IDs.

    Base CPHI format:

        <PROJECT_CODE>-<NUMERIC_ID>

    Example:

        NRGI-123456
    """
    PROJECT_CODE_LENGTH = 4
    ID_LENGTH = 6
    EXPECTED_LENGTH = PROJECT_CODE_LENGTH + 1 + ID_LENGTH  # 4 for project code, 1 for dash, 6 for ID

    #A ID is valid if it starts with a 4 digit alphanumerical number followed by a dash then a 6 digit number
    def validate(self, identifier: str, config: dict|None = None) -> dict:
        """
        Validate a base CPHI ID

        A valid CPHI ID must follow the format:

            <PROJECT_CODE>-<NUMERIC_ID>
        Validation Rules:
        - Identifier can not be missing
        - Identifier must be a string
        - Identifier can not conatin underscores (_)
        - The Identifier must have the exact length of 11 characters
        - The connector between PROJECT_CODE and NUMERIC_ID must be a dash
        - PROJECT CODE must be alphanumerical and 4 characters exactly
        - NUMERIC_ID must be 6 digits and numerical
        - The expected PROJECT_CODE must be provided to verify against serving as a benchmark
        - PROJECT_CODE must be a string

        Parameters
        ----------
        identifier:
            the identifier value that is validated
        
        config:
            Strategy configuration. For base CPHI, this would include "project_code" to enforce a specific expected project code.
        
        Returns
        -------
        dict
            Validation result with the shared strategy response shape:

            {
                "valid": bool,
                "error": str | None,
                "message": str
            }

            "valid" states whether the identifier was valid according to the formats and rules
            "error" briefly states the type of error occurred
            "message" explains the error and the details of it.
        
        Dependency Notes:
        -----------------
        The pipeline expects this method to return the same result shape as other strategies.
        If the return keys change, pipeline.py and frontend result display components may need updates.
        validation_result.py enforces that the result has the proper shape.

        """
        if identifier is None:
            return {
                "valid" : False,
                "error": "Missing identifier",
                "message": "Identifier not present."
            }
        if not isinstance(identifier, str):
            return {
                "valid" : False,
                "error": "Invalid type",
                "message": f"Expected a string identifier, but got {type(identifier).__name__}."
            }
        if "_" in identifier:
            return {
                "valid" : False,
                "error": "Invalid character",
                "message": "Base CPHI identifiers cannot contain underscores ('_')."
            }
        if len(identifier) != self.EXPECTED_LENGTH:
            return {
                "valid" : False,
                "error": "Invalid length",
                "message": f"Expected identifier length of {self.EXPECTED_LENGTH}, but got {len(identifier)}."
            }
        #--------
        #HAVE TO CHECK ID AGAINST DATABASE LATER ON
        #--------
        project_code = identifier[:CPHIStrategy.PROJECT_CODE_LENGTH]
        id_part = identifier[CPHIStrategy.PROJECT_CODE_LENGTH + 1:]
        dash = identifier[CPHIStrategy.PROJECT_CODE_LENGTH]
        expected_project = config.get("project_code")

        if dash != "-":
            return {
                "valid" : False,
                "error": "Missing dash",
                "message": f"Expected a dash ('-') at position {CPHIStrategy.PROJECT_CODE_LENGTH}, but it was not found."   
            }
        if not project_code.isalnum() or not project_code.isupper():
            return {
                "valid" : False,
                "error": "Invalid project code",
                "message": f"Project code must be upper alphanumeric, but got '{project_code}'."
            }
        if not id_part.isdigit():
            return {
                "valid" : False,
                "error": "Invalid 6 digit ID code",
                "message": f"ID part must be numeric, but got '{id_part}'."
            }
        if expected_project is not None:
            if not isinstance(expected_project,str):
                return {
                    "valid": False,
                    "error": "Invalid config",
                    "message": "Expected project_code in config to be a string."
                }
            if project_code != expected_project:
                return {
                    "valid" : False,
                    "error" : "Project code mismatch",
                    "message" : f"Identifier project code '{project_code}' does not match the expected project code '{expected_project}'."
                }
        return {
            "valid" : True,
            "error": None,
            "message": "Identifier is valid."
        }


    def generate(self, config: dict | None = None) -> str:
        """
        Generate a new base CPHI identifier

        The generated identifier follows the following format:

                <PROJECT_CODE>-<RANDOM_6_DIGIT_ID>

                The project code is a UPPER case 4 letter string
                The Random 6 digit ID is a 6 digit numerical integer
                They are both connected by a dash (-)
    
                Example:

                    NRGI-123456
        The project code is provided by config["project_code"]. The numeric ID sections is randomly generated using 6 digits.

        Parameters
        ----------
        config:
            Strategy configuration containing the required project_code value. The project code value is appended to the dash (-) connector and the RANDOM_6_DIGIT_ID
        
        Returns
        -------
        str
            Newly generated base CPHI identifier
        
        Raises
        ------
        ValueError
            Raised when a config is missing,config wasn't provided, or project_code is not a valid 4 character
            uppercase alphanumeric string.
        
        Dependency Notes
        ----------------
        The generation pipeline calls this method when it needs to create IDs for
        rows with missing identifiers. Generated IDs are later check by the pipeline for conflicts against existing and other generated IDs.
        The pipeline calls all generate functions with the same parameters and expects a str output from the generate function. Any changes should still maintain the consistency throughout all generate functions.
        """
        if config is None or "project_code" not in config:
            raise ValueError("Missing config for CPHI generation. 'project_code' is required.")

        project_code = config.get("project_code")

        if not isinstance(project_code, str):
            raise ValueError("project_code must be a string.")

        if len(project_code) != self.PROJECT_CODE_LENGTH:
            raise ValueError("project_code must be 4 characters.")

        if not project_code.isalnum() or not project_code.isupper():
            raise ValueError("project_code must be uppercase alphanumeric.")

        random_digits = random.choices(string.digits, k=self.ID_LENGTH)
        random_id = "".join(random_digits)

        return f"{project_code}-{random_id}"
        