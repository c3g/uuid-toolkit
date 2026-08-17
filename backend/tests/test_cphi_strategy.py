import re

import pytest

from app.strategies.cphi import CPHIStrategy


def test_validate_valid_cphi():
    strategy = CPHIStrategy()

    result = strategy.validate(
        "NRGI-123456",
        {"project_code": "NRGI"},
    )

    assert result["valid"] is True
    assert result["error"] is None


def test_validate_missing_identifier():
    strategy = CPHIStrategy()

    result = strategy.validate(
        None,
        {"project_code": "NRGI"},
    )

    assert result["valid"] is False
    assert result["error"] == "Missing identifier"


def test_validate_non_string_identifier():
    strategy = CPHIStrategy()

    result = strategy.validate(
        123456,
        {"project_code": "NRGI"},
    )

    assert result["valid"] is False
    assert result["error"] == "Invalid type"


def test_validate_rejects_variant_identifier():
    strategy = CPHIStrategy()

    result = strategy.validate(
        "NRGI-123456_EXP_0001",
        {"project_code": "NRGI"},
    )

    assert result["valid"] is False
    assert result["error"] == "Invalid character"


def test_validate_invalid_length():
    strategy = CPHIStrategy()

    result = strategy.validate(
        "NRGI-12345",
        {"project_code": "NRGI"},
    )

    assert result["valid"] is False
    assert result["error"] == "Invalid length"


def test_validate_missing_dash():
    strategy = CPHIStrategy()

    result = strategy.validate(
        "NRGI_123456".replace("_", "X"),
        {"project_code": "NRGI"},
    )

    assert result["valid"] is False
    assert result["error"] == "Missing dash"


def test_validate_lowercase_project_code():
    strategy = CPHIStrategy()

    result = strategy.validate(
        "nrgi-123456",
        {"project_code": "NRGI"},
    )

    assert result["valid"] is False
    assert result["error"] == "Invalid project code"


def test_validate_non_numeric_id():
    strategy = CPHIStrategy()

    result = strategy.validate(
        "NRGI-ABCDEF",
        {"project_code": "NRGI"},
    )

    assert result["valid"] is False
    assert result["error"] == "Invalid 6 digit ID code"


def test_validate_project_code_mismatch():
    strategy = CPHIStrategy()

    result = strategy.validate(
        "ABCD-123456",
        {"project_code": "NRGI"},
    )

    assert result["valid"] is False
    assert result["error"] == "Project code mismatch"


def test_validate_invalid_project_code_config_type():
    strategy = CPHIStrategy()

    result = strategy.validate(
        "NRGI-123456",
        {"project_code": 1234},
    )

    assert result["valid"] is False
    assert result["error"] == "Invalid config"


def test_generate_valid_cphi():
    strategy = CPHIStrategy()

    generated = strategy.generate(
        {"project_code": "NRGI"},
    )

    assert re.fullmatch(r"NRGI-\d{6}", generated)


def test_generate_missing_config_raises_error():
    strategy = CPHIStrategy()

    with pytest.raises(
        ValueError,
        match="Missing config for CPHI generation",
    ):
        strategy.generate(None)


def test_generate_missing_project_code_raises_error():
    strategy = CPHIStrategy()

    with pytest.raises(
        ValueError,
        match="Missing config for CPHI generation",
    ):
        strategy.generate({})


def test_generate_non_string_project_code_raises_error():
    strategy = CPHIStrategy()

    with pytest.raises(
        ValueError,
        match="project_code must be a string",
    ):
        strategy.generate({"project_code": 1234})


def test_generate_wrong_length_project_code_raises_error():
    strategy = CPHIStrategy()

    with pytest.raises(
        ValueError,
        match="project_code must be 4 characters",
    ):
        strategy.generate({"project_code": "ABC"})


def test_generate_lowercase_project_code_raises_error():
    strategy = CPHIStrategy()

    with pytest.raises(
        ValueError,
        match="project_code must be uppercase alphanumeric",
    ):
        strategy.generate({"project_code": "nrgi"})