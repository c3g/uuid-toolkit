import uuid

import pytest

from app.strategies.uuid_standard import UUIDStrategy


def test_validate_valid_uuid_v4():
    strategy = UUIDStrategy()
    identifier = str(uuid.uuid4())

    result = strategy.validate(
        identifier,
        {"version": 4},
    )

    assert result["valid"] is True
    assert result["error"] is None


def test_validate_invalid_uuid_string():
    strategy = UUIDStrategy()

    result = strategy.validate(
        "not-a-valid-uuid",
        {"version": 4},
    )

    assert result["valid"] is False
    assert result["error"] == "Invalid UUID format"


def test_validate_wrong_uuid_version():
    strategy = UUIDStrategy()
    identifier = str(uuid.uuid1())

    result = strategy.validate(
        identifier,
        {"version": 4},
    )

    assert result["valid"] is False
    assert result["error"] == "UUID version mismatch"


def test_validate_missing_identifier():
    strategy = UUIDStrategy()

    result = strategy.validate(
        None,
        {"version": 4},
    )

    assert result["valid"] is False
    assert result["error"] == "Missing identifier"


def test_validate_non_string_identifier():
    strategy = UUIDStrategy()

    result = strategy.validate(
        12345,
        {"version": 4},
    )

    assert result["valid"] is False
    assert result["error"] == "Invalid type"


def test_validate_missing_config():
    strategy = UUIDStrategy()
    identifier = str(uuid.uuid4())

    result = strategy.validate(
        identifier,
        None,
    )

    assert result["valid"] is False
    assert result["error"] == (
        "Missing config or version for UUID validation"
    )


def test_generate_uuid_v4():
    strategy = UUIDStrategy()

    generated = strategy.generate(
        {"version": 4},
    )

    parsed = uuid.UUID(generated)

    assert parsed.version == 4
    assert str(parsed) == generated


def test_generate_missing_config_raises_error():
    strategy = UUIDStrategy()

    with pytest.raises(
        ValueError,
        match="Missing config",
    ):
        strategy.generate(None)


def test_generate_unsupported_version_raises_error():
    strategy = UUIDStrategy()

    with pytest.raises(
        ValueError,
        match="Unsupported UUID version",
    ):
        strategy.generate({"version": 7})