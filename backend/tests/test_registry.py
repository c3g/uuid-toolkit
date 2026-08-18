import pytest

from app.strategies.cphi import CPHIStrategy
from app.strategies.custom import CustomStrategy
from app.strategies.pcgl import PCGLStrategy
from app.strategies.pcgl_modifiers import PCGL_Modifiers
from app.strategies.registry import get_strategy
from app.strategies.uuid_standard import UUIDStrategy


# ------------------------------------------------------------------
# General registry behavior
# ------------------------------------------------------------------


def test_registry_normalizes_strategy_name():
    strategy = get_strategy(
        "  uuid  ",
        {"version": 4},
    )

    assert isinstance(strategy, UUIDStrategy)


def test_unknown_strategy_raises_error():
    with pytest.raises(
        ValueError,
        match="was not found in the registry",
    ):
        get_strategy(
            "UNKNOWN",
            {},
        )


# ------------------------------------------------------------------
# UUID
# ------------------------------------------------------------------


def test_registry_returns_uuid_strategy():
    strategy = get_strategy(
        "UUID",
        {"version": 4},
    )

    assert isinstance(strategy, UUIDStrategy)


def test_registry_uuid_requires_version():
    with pytest.raises(ValueError):
        get_strategy(
            "UUID",
            {},
        )


def test_registry_rejects_unsupported_uuid_version():
    with pytest.raises(ValueError):
        get_strategy(
            "UUID",
            {"version": 7},
        )


# ------------------------------------------------------------------
# CPHI
# ------------------------------------------------------------------


def test_registry_returns_cphi_strategy_for_sample():
    strategy = get_strategy(
        "CPHI",
        {
            "project_code": "NRGI",
            "entity_type": "sample",
        },
    )

    assert isinstance(strategy, CPHIStrategy)


def test_registry_returns_cphi_strategy_for_patient():
    strategy = get_strategy(
        "CPHI",
        {
            "project_code": "NRGI",
            "entity_type": "patient",
        },
    )

    assert isinstance(strategy, CPHIStrategy)


def test_registry_cphi_requires_project_code():
    with pytest.raises(ValueError):
        get_strategy(
            "CPHI",
            {
                "entity_type": "sample",
            },
        )


def test_registry_cphi_requires_entity_type():
    with pytest.raises(ValueError):
        get_strategy(
            "CPHI",
            {
                "project_code": "NRGI",
            },
        )


def test_registry_rejects_invalid_cphi_entity_type():
    with pytest.raises(ValueError):
        get_strategy(
            "CPHI",
            {
                "project_code": "NRGI",
                "entity_type": "invalid",
            },
        )


def test_registry_cphi_does_not_switch_to_modifier_strategy():
    strategy = get_strategy(
        "CPHI",
        {
            "project_code": "NRGI",
            "entity_type": "sample",
            "variant": "EXP",
        },
    )

    assert isinstance(strategy, CPHIStrategy)


# ------------------------------------------------------------------
# Base PCGL
# ------------------------------------------------------------------


def test_registry_returns_base_pcgl_without_variant():
    strategy = get_strategy(
        "PCGL",
        {
            "project_code": "NRGI",
            "entity_type": "sample",
        },
    )

    assert isinstance(strategy, PCGLStrategy)


def test_registry_returns_base_pcgl_with_empty_variants():
    strategy = get_strategy(
        "PCGL",
        {
            "project_code": "NRGI",
            "entity_type": "sample",
            "variants": [],
        },
    )

    assert isinstance(strategy, PCGLStrategy)


def test_registry_pcgl_requires_project_code():
    with pytest.raises(ValueError):
        get_strategy(
            "PCGL",
            {
                "entity_type": "sample",
            },
        )


def test_registry_pcgl_requires_entity_type():
    with pytest.raises(ValueError):
        get_strategy(
            "PCGL",
            {
                "project_code": "NRGI",
            },
        )


# ------------------------------------------------------------------
# PCGL variants
# ------------------------------------------------------------------


def test_registry_returns_pcgl_modifier_for_sample_variant():
    strategy = get_strategy(
        "PCGL",
        {
            "project_code": "NRGI",
            "entity_type": "sample",
            "variant": "EXP",
        },
    )

    assert isinstance(strategy, PCGL_Modifiers)


def test_registry_returns_pcgl_modifier_for_patient_variant():
    strategy = get_strategy(
        "PCGL",
        {
            "project_code": "NRGI",
            "entity_type": "patient",
            "variant": "SPE",
        },
    )

    assert isinstance(strategy, PCGL_Modifiers)


def test_registry_returns_pcgl_modifier_for_multiple_variants():
    strategy = get_strategy(
        "PCGL",
        {
            "project_code": "NRGI",
            "entity_type": "sample",
            "variants": ["EXP", "LIB"],
        },
    )

    assert isinstance(strategy, PCGL_Modifiers)


def test_registry_rejects_sample_spe_variant():
    with pytest.raises(ValueError):
        get_strategy(
            "PCGL",
            {
                "project_code": "NRGI",
                "entity_type": "sample",
                "variant": "SPE",
            },
        )


def test_registry_rejects_patient_exp_variant():
    with pytest.raises(ValueError):
        get_strategy(
            "PCGL",
            {
                "project_code": "NRGI",
                "entity_type": "patient",
                "variant": "EXP",
            },
        )


def test_registry_rejects_invalid_variant_in_multiple_variants():
    with pytest.raises(ValueError):
        get_strategy(
            "PCGL",
            {
                "project_code": "NRGI",
                "entity_type": "sample",
                "variants": ["EXP", "BAD"],
            },
        )


def test_registry_normalizes_pcgl_variant_case():
    strategy = get_strategy(
        "PCGL",
        {
            "project_code": "NRGI",
            "entity_type": "sample",
            "variant": " exp ",
        },
    )

    assert isinstance(strategy, PCGL_Modifiers)


# ------------------------------------------------------------------
# CUSTOM
# ------------------------------------------------------------------


def test_registry_returns_fixed_custom_strategy():
    strategy = get_strategy(
        "CUSTOM",
        {
            "prefix_mode": "fixed",
            "fixed_prefix": "C3G",
            "connector": "-",
            "suffix_type": "numeric",
            "suffix_length": 6,
        },
    )

    assert isinstance(strategy, CustomStrategy)


def test_registry_returns_random_custom_strategy():
    strategy = get_strategy(
        "CUSTOM",
        {
            "prefix_mode": "random",
            "prefix_type": "letters",
            "prefix_length": 4,
            "connector": "_",
            "suffix_type": "numeric",
            "suffix_length": 5,
        },
    )

    assert isinstance(strategy, CustomStrategy)