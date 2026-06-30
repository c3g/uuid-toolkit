"""
PCGL Modifier strategy.

This model defines the validation and generation logic for PCGL Variant Identifiers. A modified PCGL Variant Modifier has the following format:

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

This module only handles PCGL Variant identifiers. It uses pcgl.py to help validated and generate the base PCGL ID component of the identifier.

Dependency notes:
- registry.py decides when to use PCGL Modifiers.
- api/utils.py should validate PCGL config values before this strategy is used.
- pipeline.py calls validate () and generate() through the shared strategy interface. So the return shape of validate() and generate() should stay consistent. Validate results are enforced through validation_result.py.
- ConfigPanel.jsx controls which variants the user can select in the frontend.

"""
from .base import StrategyInterface
from .pcgl import PCGLStrategy
import random
import string


class PCGL_Modifiers(StrategyInterface):
    """
    Strategy for validating and generating PCGL identifiers with variants.

    This calss extends the base PCGL identifier by adding a variant section and a variant specific 4 digit ID.

    Modified PCGL format:

        <BASE_PCGL>_<VARIANT>_<4_DIGIT_ID>

    Example:
        NRGI-123456_EXP_0001
    The base PCGL component is validated using PCGLStrategy. This class is only responsible for validating the extra variant and 4_DIGIT_ID sections.

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
        self.base_strategy = PCGLStrategy()

    def validate(self, identifier: str, config: dict | None = None) -> dict:
        """
        Validates a modified PCGL identifier that is a variant

        A valid PCGL variant ID must follow the following format:

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
                "message": "Missing 'variant' in config for PCGL modifier validation."
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
            "message": "Modified PCGL identifier is valid."
        }

    def generate(self, config: dict | None = None) -> str:
        """
        Generate a new PCGL identifier variant of a desired type.

        The generated identifier follows the following format:

            <BASE_PCGL>_<VARIANT>_<4_DIGIT_ID>

        Example:
            NRGI-123456_EXP_0001

        The base PCGL is generated by the generate() method in PCGLStrategy
        The variant section comes from the config["variant"] section in whicht the user 
        passes as input the type of variant. The 4 digit ID is randomly generated using the random library.

        Parameters
        ----------
        config:
            A strategy configuration stored in a dict. It contains values need by the base PCGL generator
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
            raise ValueError("Missing 'variant' in config for PCGL modifier generation.")

        if variant not in self.ALLOWED_VARIANTS:
            raise ValueError(
                f"Invalid variant '{variant}'. Allowed values: {sorted(self.ALLOWED_VARIANTS)}."
            )

        base_id = self.base_strategy.generate(config)

        modifier_id = "".join(
            random.choices(string.digits, k=self.MODIFIER_ID_LENGTH)
        )

        return f"{base_id}_{variant}_{modifier_id}"
    
    def get_strategy_info(self, config: dict | None= None) -> dict:
        config = config or {}

        if config.get("variants"):
            return {
                "generation_mode":"derive_from_existing",
                "output_mode":"multiple_columns",
                "requires_existing_identifier": True,
                "preserve_input_identifier":True,
            }
        return super().get_strategy_info(config)
    
    def generate_derived_identifiers(self, source_identifier: str, config:dict | None = None) -> dict[str,str]:
        """
        Generate one or more PCGL variant identifiers from an exisitng base PCGL ID

        Example:
        source_identifier:
            NRGI-123456

        config:
            {
                "project_code": "NRGI",
                "entity_type": "sample",
                "variants": ["EXP", "LIB"]
            }

        returns:
            {
                "pcgl_EXP_id": "NRGI-123456_EXP_4829",
                "pcgl_LIB_id": "NRGI-123456_LIB_1038"
            }
        """
        config = config or {}

        variants = config.get("variants", [])

        if not variants:
            raise ValueError("Missing 'variants' for PCGL derived generation of identifiers.")
        
        base_result = self.base_strategy.validate(source_identifier, config)

        if base_result["valid"] is not True:
            raise ValueError(base_result["message"])
        
        generated_outputs: dict[str,str] = {}

        for variant in variants:
            if variant not in self.ALLOWED_VARIANTS:
                raise ValueError(
                    f"Invalid vairant:'{variant}'."
                    f"Allowed values: {sorted(self.ALLOWED_VARIANTS)}"
                )
            modifier_id = "".join(
                random.choices(string.digits, k=self.MODIFIER_ID_LENGTH)
            )
            generated_outputs[variant] = f"{source_identifier}_{variant}_{modifier_id}"


        return generated_outputs