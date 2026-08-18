import re

import pytest

from app.strategies.pcgl import PCGLStrategy
from app.strategies.pcgl_modifiers import PCGL_Modifiers


# ------------------------------------------------------------------
# Base PCGL
# ------------------------------------------------------------------


def test_validate_valid_base_pcgl():
    strategy = PCGLStrategy()

    result = strategy.validate(
        "NRGI-123456",
        {"project_code": "NRGI"},
    )

    assert result["valid"] is True
    assert result["error"] is None


def test_base_pcgl_rejects_variant_identifier():
    strategy = PCGLStrategy()

    result = strategy.validate(
        "NRGI-123456_EXP_0001",
        {"project_code": "NRGI"},
    )

    assert result["valid"] is False
    assert result["error"] == "Invalid character"


def test_validate_base_pcgl_project_code_mismatch():
    strategy = PCGLStrategy()

    result = strategy.validate(
        "ABCD-123456",
        {"project_code": "NRGI"},
    )

    assert result["valid"] is False
    assert result["error"] == "Project code mismatch"


def test_generate_base_pcgl():
    strategy = PCGLStrategy()

    generated = strategy.generate(
        {"project_code": "NRGI"},
    )

    assert re.fullmatch(r"NRGI-\d{6}", generated)


def test_generate_base_pcgl_missing_config_raises_error():
    strategy = PCGLStrategy()

    with pytest.raises(
        ValueError,
        match="Missing config for PCGL generation",
    ):
        strategy.generate(None)


# ------------------------------------------------------------------
# PCGL variants
# ------------------------------------------------------------------


def test_validate_valid_pcgl_variant():
    strategy = PCGL_Modifiers()

    result = strategy.validate(
        "NRGI-123456_EXP_0001",
        {
            "project_code": "NRGI",
            "variant": "EXP",
        },
    )

    assert result["valid"] is True
    assert result["error"] is None


def test_validate_pcgl_variant_missing_variant_config():
    strategy = PCGL_Modifiers()

    result = strategy.validate(
        "NRGI-123456_EXP_0001",
        {
            "project_code": "NRGI",
        },
    )

    assert result["valid"] is False
    assert result["error"] == "Missing variant"


def test_validate_pcgl_variant_wrong_marker():
    strategy = PCGL_Modifiers()

    result = strategy.validate(
        "NRGI-123456_RG_0001",
        {
            "project_code": "NRGI",
            "variant": "EXP",
        },
    )

    assert result["valid"] is False
    assert result["error"] == "Missing variant marker"


def test_validate_pcgl_variant_invalid_modifier_length():
    strategy = PCGL_Modifiers()

    result = strategy.validate(
        "NRGI-123456_EXP_001",
        {
            "project_code": "NRGI",
            "variant": "EXP",
        },
    )

    assert result["valid"] is False
    assert result["error"] == "Invalid modifier ID length"


def test_validate_pcgl_variant_non_numeric_modifier():
    strategy = PCGL_Modifiers()

    result = strategy.validate(
        "NRGI-123456_EXP_ABCD",
        {
            "project_code": "NRGI",
            "variant": "EXP",
        },
    )

    assert result["valid"] is False
    assert result["error"] == "Invalid modifier ID"


def test_generate_pcgl_variant():
    strategy = PCGL_Modifiers()

    generated = strategy.generate(
        {
            "project_code": "NRGI",
            "variant": "EXP",
        },
    )

    assert re.fullmatch(
        r"NRGI-\d{6}_EXP_\d{4}",
        generated,
    )


def test_generate_pcgl_variant_missing_variant_raises_error():
    strategy = PCGL_Modifiers()

    with pytest.raises(
        ValueError,
        match="Missing 'variant'",
    ):
        strategy.generate(
            {"project_code": "NRGI"},
        )


def test_generate_pcgl_variant_invalid_variant_raises_error():
    strategy = PCGL_Modifiers()

    with pytest.raises(
        ValueError,
        match="Invalid variant",
    ):
        strategy.generate(
            {
                "project_code": "NRGI",
                "variant": "BAD",
            },
        )


# ------------------------------------------------------------------
# Derived PCGL generation
# ------------------------------------------------------------------


def test_generate_multiple_derived_pcgl_variants():
    strategy = PCGL_Modifiers()

    generated = strategy.generate_derived_identifiers(
        "NRGI-123456",
        {
            "project_code": "NRGI",
            "variants": ["EXP", "LIB"],
        },
    )

    assert set(generated) == {"EXP", "LIB"}

    assert re.fullmatch(
        r"NRGI-123456_EXP_\d{4}",
        generated["EXP"],
    )

    assert re.fullmatch(
        r"NRGI-123456_LIB_\d{4}",
        generated["LIB"],
    )


def test_generate_derived_pcgl_requires_variants():
    strategy = PCGL_Modifiers()

    with pytest.raises(
        ValueError,
        match="Missing 'variants'",
    ):
        strategy.generate_derived_identifiers(
            "NRGI-123456",
            {
                "project_code": "NRGI",
                "variants": [],
            },
        )


def test_generate_derived_pcgl_rejects_invalid_base():
    strategy = PCGL_Modifiers()

    with pytest.raises(ValueError):
        strategy.generate_derived_identifiers(
            "BAD-ID",
            {
                "project_code": "NRGI",
                "variants": ["EXP"],
            },
        )


def test_pcgl_modifier_reports_derived_generation_mode():
    strategy = PCGL_Modifiers()

    info = strategy.get_strategy_info(
        {
            "project_code": "NRGI",
            "variants": ["EXP", "LIB"],
        },
    )

    assert info == {
        "generation_mode": "derive_from_existing",
        "output_mode": "multiple_columns",
        "requires_existing_identifier": True,
        "preserve_input_identifier": True,
    }