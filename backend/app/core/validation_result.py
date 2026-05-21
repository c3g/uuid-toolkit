

def enforce_validation_result(result: dict) -> dict:
    """
    Enforce the ValidationResult schema.

    Raises ValueError if the schema is invalid.
    """
    if not isinstance(result, dict):
        raise ValueError(
            f"Validation result must be a dict, got {type(result).__name__}"
        )

    required_keys = {"valid", "error", "message"}

    missing = required_keys - result.keys()
    extra = result.keys() - required_keys

    if missing:
        raise ValueError(f"Validation result missing keys: {missing}")

    if extra:
        raise ValueError(f"Validation result has extra keys: {extra}")

    if not isinstance(result["valid"], bool):
        raise ValueError("'valid' must be a boolean")

    if result["error"] is not None and not isinstance(result["error"], str):
        raise ValueError("'error' must be a string or None")

    if not isinstance(result["message"], str):
        raise ValueError("'message' must be a string")


    return result