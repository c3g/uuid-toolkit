import re

import pytest

from app.strategies.custom import CustomStrategy


# ------------------------------------------------------------------
# Fixed-prefix CUSTOM
# ------------------------------------------------------------------


def test_validate_valid_fixed_prefix_identifier():
    strategy = CustomStrategy(
        prefix_mode="fixed",
        fixed_prefix="C3G",
        connector="-",
        suffix_type="numeric",
        suffix_length=6,
    )

    result = strategy.validate("C3G-123456")

    assert result["valid"] is True
    assert result["error"] is None


def test_validate_wrong_fixed_prefix():
    strategy = CustomStrategy(
        prefix_mode="fixed",
        fixed_prefix="C3G",
        connector="-",
        suffix_type="numeric",
        suffix_length=6,
    )

    result = strategy.validate("ABC-123456")

    assert result["valid"] is False
    assert result["error"] == "Invalid fixed prefix"


def test_validate_wrong_connector():
    strategy = CustomStrategy(
        prefix_mode="fixed",
        fixed_prefix="C3G",
        connector="-",
        suffix_type="numeric",
        suffix_length=6,
    )

    result = strategy.validate("C3G_123456")

    assert result["valid"] is False
    assert result["error"] == "Invalid connector"


def test_validate_wrong_suffix_type():
    strategy = CustomStrategy(
        prefix_mode="fixed",
        fixed_prefix="C3G",
        connector="-",
        suffix_type="numeric",
        suffix_length=6,
    )

    result = strategy.validate("C3G-ABCDEF")

    assert result["valid"] is False
    assert result["error"] == "Invalid suffix"


def test_validate_wrong_identifier_length():
    strategy = CustomStrategy(
        prefix_mode="fixed",
        fixed_prefix="C3G",
        connector="-",
        suffix_type="numeric",
        suffix_length=6,
    )

    result = strategy.validate("C3G-12345")

    assert result["valid"] is False
    assert result["error"] == "Invalid length"


def test_validate_missing_identifier():
    strategy = CustomStrategy(
        prefix_mode="fixed",
        fixed_prefix="C3G",
        connector="-",
        suffix_type="numeric",
        suffix_length=6,
    )

    result = strategy.validate(None)

    assert result["valid"] is False
    assert result["error"] == "Missing identifier"


def test_validate_non_string_identifier():
    strategy = CustomStrategy(
        prefix_mode="fixed",
        fixed_prefix="C3G",
        connector="-",
        suffix_type="numeric",
        suffix_length=6,
    )

    result = strategy.validate(123456)

    assert result["valid"] is False
    assert result["error"] == "Invalid type"


def test_generate_fixed_prefix_identifier():
    strategy = CustomStrategy(
        prefix_mode="fixed",
        fixed_prefix="C3G",
        connector="-",
        suffix_type="numeric",
        suffix_length=6,
    )

    generated = strategy.generate()

    assert re.fullmatch(r"C3G-\d{6}", generated)


# ------------------------------------------------------------------
# Random-prefix CUSTOM
# ------------------------------------------------------------------


def test_generate_random_letters_prefix():
    strategy = CustomStrategy(
        prefix_mode="random",
        prefix_type="letters",
        prefix_length=4,
        connector="_",
        suffix_type="numeric",
        suffix_length=5,
    )

    generated = strategy.generate()

    assert re.fullmatch(r"[A-Z]{4}_\d{5}", generated)


def test_generated_random_identifier_validates():
    strategy = CustomStrategy(
        prefix_mode="random",
        prefix_type="alphanumeric",
        prefix_length=4,
        connector="+",
        suffix_type="letters",
        suffix_length=3,
    )

    generated = strategy.generate()
    result = strategy.validate(generated)

    assert result["valid"] is True
    assert result["error"] is None


def test_generate_without_connector():
    strategy = CustomStrategy(
        prefix_mode="fixed",
        fixed_prefix="ABC",
        connector="",
        suffix_type="numeric",
        suffix_length=4,
    )

    generated = strategy.generate()

    assert re.fullmatch(r"ABC\d{4}", generated)


# ------------------------------------------------------------------
# Configuration validation
# ------------------------------------------------------------------


def test_invalid_prefix_mode_raises_error():
    with pytest.raises(ValueError):
        CustomStrategy(
            prefix_mode="bad",
            fixed_prefix="C3G",
            connector="-",
            suffix_type="numeric",
            suffix_length=6,
        )


def test_invalid_connector_raises_error():
    with pytest.raises(ValueError):
        CustomStrategy(
            prefix_mode="fixed",
            fixed_prefix="C3G",
            connector=":",
            suffix_type="numeric",
            suffix_length=6,
        )


def test_invalid_suffix_type_raises_error():
    with pytest.raises(ValueError):
        CustomStrategy(
            prefix_mode="fixed",
            fixed_prefix="C3G",
            connector="-",
            suffix_type="symbols",
            suffix_length=6,
        )


def test_non_positive_suffix_length_raises_error():
    with pytest.raises(ValueError):
        CustomStrategy(
            prefix_mode="fixed",
            fixed_prefix="C3G",
            connector="-",
            suffix_type="numeric",
            suffix_length=0,
        )


def test_fixed_mode_requires_fixed_prefix():
    with pytest.raises(ValueError):
        CustomStrategy(
            prefix_mode="fixed",
            connector="-",
            suffix_type="numeric",
            suffix_length=6,
        )


def test_random_mode_requires_prefix_type():
    with pytest.raises(ValueError):
        CustomStrategy(
            prefix_mode="random",
            prefix_length=4,
            connector="-",
            suffix_type="numeric",
            suffix_length=6,
        )


def test_random_mode_requires_positive_prefix_length():
    with pytest.raises(ValueError):
        CustomStrategy(
            prefix_mode="random",
            prefix_type="letters",
            prefix_length=0,
            connector="-",
            suffix_type="numeric",
            suffix_length=6,
        )