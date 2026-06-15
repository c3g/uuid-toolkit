from .base import StrategyInterface
import string
import random

class CPHIStrategy(StrategyInterface):
    PROJECT_CODE_LENGTH = 4
    ID_LENGTH = 6
    EXPECTED_LENGTH = PROJECT_CODE_LENGTH + 1 + ID_LENGTH  # 4 for project code, 1 for dash, 6 for ID

    #A ID is valid if it starts with a 4 digit alphanumerical number followed by a dash then a 6 digit number
    def validate(self, identifier: str, config: dict|None = None) -> dict:
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
        