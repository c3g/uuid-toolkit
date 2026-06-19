"""
CPHI Modifier strategy.

This model defines the validation and generation logic for CPHI Variant Identifiers. A modified CPHI Variant Modifier has the following format:

    <PROJECT_CODE>-<NUMERIC_ID>_<VARIANT>_<4_DIGIT_ID>

    Example:
        NRGI-123456_SPE_7890

Rules enforced by this strategy:
- The project code is a UPPER case 4 letter string
- The numeric ID is a 6 digit numerical integer
- The project_code and numeric id are both connected by a dash (-)
- The variant is the concatenated string variant identifier that defines what kind of variant the ID is.
- The 4 digit ID is a 4 digit random number that helps identify the right variant
- Once provided config[project_code], the identifier's project code must match the one provided by the user
- config[variant] should also be provided by the user and the identifier's VARIANT field must match the one provided
- A variant identifier can have the 4_DIGIT_ID repeat across multiple samples or patients as long as the complete identifier remains universally unique.

This module only handles CPHI Variant identifiers. It uses cphi.py to help validatem and generate the base CPHI ID component of the identifier.

Dependency notes:
- registry.py decides when to use CPHI Modifiers.
- api/utils.py should validate CPHI config values before this strategy is used.
- pipeline.py calls validate () and generate() through the shared strategy interface. So the return shape of validate() and generate() should stay consistent. Validate results are enforced through validation_result.py.
- ConfigPanel.jsx controls which variants the user can select in the frontend.

"""
from .base import StrategyInterface
from .cphi import CPHIStrategy
import random
import string


class CPHI_Modifiers(StrategyInterface):
    """
    Strategy for validating and generating CPHI identifiers with variants.

    This calss extends the base CPHI identifier by adding a variant section and a variant specific 4 digit ID.

    Modified CPHI format:

        <BASE_CPHI>_<VARIANT>_<4_DIGIT_ID>

    Example:
        NRGI-123456_EXP_0001
    The base cphi component is validated using CPHIStrategy. This class is only responsible for validating the extra variant and 4_DIGIT_ID sections.

    Examples of variants:
    - SPE: specimen-related patient identifier
    - EXP: experiment identifier
    - LIB: library identifier
    - RG: read group identifier
    - WRK: workflow identifier
    - ANA: analysis identifier
    """
    MODIFIER_ID_LENGTH = 4
    ALLOWED_VARIANTS = {"SPE", "EXP", "LIB", "RG", "WRK", "ANA"}

    def __init__(self):
        self.base_strategy = CPHIStrategy()

    def validate(self, identifier: str, config: dict | None = None) -> dict:
        """
        Validates a modified CPHI identifier that is a variant

        A valid CPHI variant ID must follow the following format:

            <PROJECT_CODE>-<NUMERIC_ID>_<VARIANT>_<4_DIGIT_ID>

            Example:
                NRGI-123456_SPE_7890
        
        Validation Rules:
        -config[variant] must not be empty and it must be in the allowed subset of ALLOWED_VARIANTS depending on if its a sample or patient ID.
        -The identifier must be present
        -The identifier must be a string
        -The expected marker of a variant being _variant_ such as _EXP_ should be in the identifier
        -The identifier must be split into three sections:
            1) Base CPHI identifier
            2) Variant marker
            3) 4 Digit ID
        -The base CPHI identifier must be valid according to CPHIStrategy
        -The variant marker must match the expected variant provided by config
        -The variant marker must have the right length based on the expected variant
        -The 4 digit ID must be numerical only and 4 digits long

        Parameters
        ----------
        identifier:
            Identifier value to validate
        config:
            A dict that contains the expected values to validate against such as the project code, sample or patient type, and the variant type.
        
        Returns
        -------
        dict
            validation result with the following shape:

            {
                "valid": bool,
                "error": str | None,
                "message": str,
            }
        
        Dependency Notes
        ----------------
        The pipeline expects and depends on this method to return the same result shape as the other strategies.
        If the return keys or shape changes, pipeline.py and frontend result display components may also need updates.
        The generation pipeline also depends on this function when there is an existing value in the provided file to check if
        the existing value was a valid ID.
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
        """
        Generate a new CPHI identifier variant of a desired type.

        The generated identifier follows the following format:

            <BASE_CPHI>_<VARIANT>_<4_DIGIT_ID>

        Example:
            NRGI-123456_EXP_0001

        The base CPHI is generated by the generate() method in CPHIStrategy
        The variant section comes from the config["variant"] section in whicht the user 
        passes as input the type of variant. The 4 digit ID is randomly generated using the random library.

        Parameters
        ----------
        config:
            A strategy configuration stored in a dict. It contains values need by the base CPHI generator
            as well as the choice between sample and patient type and the subsequent variant type.
        
        Returns
        -------
        str
            It return the generated string identifier that matches the specifications shown above
        
        Raises
        ------
        Value Error
            Raised when config values are missing or invalid depending on they type of value needed
        
        Dependency Notes
        ----------------
        The generation pipeline calls this method for rows that don't contain an existing value.
        The pipeline later check generated IDs for conflicts within the existing file, and generated values.
        The variants generated depend on config passing on a input that is without underscores.
        If the frontend/API passes on values that contain anything other than the right abbreviations it could create invalid identifiers.
        """
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