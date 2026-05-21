import uuid
from app.strategies.uuid_standard import UUIDStrategy


def test_validate_valid_uuid_v4():
    strategy = UUIDStrategy()
    valid = str(uuid.uuid4())
    result = strategy.validate(valid, {"version": 4})

    assert result["valid"] is True
    assert result["error"] is None


def test_validate_invalid_string():
    strategy = UUIDStrategy()
    result = strategy.validate("not-a-uuid", {"version": 4})

    assert result["valid"] is False
    assert result["error"] == "Invalid UUID format"


def test_validate_wrong_version():
    strategy = UUIDStrategy()
    v1 = str(uuid.uuid1())
    result = strategy.validate(v1, {"version": 4})

    assert result["valid"] is False
    assert result["error"] == "UUID version mismatch"


def test_generate_uuid_v4():
    strategy = UUIDStrategy()
    generated = strategy.generate({"version": 4})
    parsed = uuid.UUID(generated)

    assert parsed.version == 4