import re
import uuid
import pytest

from core.pipeline import run_validation_pipeline, run_generation_pipeline


def to_bytes(text: str) -> bytes:
    return text.encode("utf-8")


def test_uuid_validation_pipeline_valid_and_invalid_rows():
    valid_uuid = str(uuid.uuid4())

    csv_text = f"""uuid,sample_name
{valid_uuid},sample_1
not-a-uuid,sample_2
"""

    result = run_validation_pipeline(
        file_bytes=to_bytes(csv_text),
        file_type="csv",
        strategy_name="UUID",
        config={"version": 4},
        id_name="uuid",
    )

    assert result["mode"] == "validation"
    assert result["summary"]["total_rows"] == 2
    assert result["summary"]["valid_count"] == 1
    assert result["summary"]["invalid_count"] == 1
    assert result["summary"]["duplicate_count"] == 0
    assert result["summary"]["clean_count"] == 1

    assert len(result["clean_records"]) == 1

    assert result["results"][0]["valid"] is True
    assert result["results"][1]["valid"] is False
    assert result["results"][1]["error"] == "Invalid UUID format"


def test_uuid_generation_pipeline_generates_only_missing_ids():
    existing_uuid = str(uuid.uuid4())

    csv_text = f"""uuid,sample_name
,sample_1
{existing_uuid},sample_2
"""

    result = run_generation_pipeline(
        file_bytes=to_bytes(csv_text),
        file_type="csv",
        strategy_name="UUID",
        config={"version": 4},
        id_name="uuid",
    )

    assert result["mode"] == "generation"
    assert result["summary"]["total_rows"] == 2
    assert result["summary"]["generated_count"] == 1
    assert result["summary"]["skipped_count"] == 1
    assert result["summary"]["duplicate_count"] == 0
    assert result["summary"]["generation_conflict_count"] == 0
    assert result["summary"]["error_count"] == 0
    assert result["summary"]["clean_count"] == 2

    updated_records = result["updated_records"]

    generated_uuid = updated_records[0]["uuid"]
    parsed = uuid.UUID(generated_uuid)

    assert parsed.version == 4
    assert updated_records[1]["uuid"] == existing_uuid

    assert result["results"][0]["action"] == "generated"
    assert result["results"][0]["valid"] is True
    assert result["results"][1]["action"] == "skipped_existing_id"
    assert result["results"][1]["valid"] is True

    assert len(result["clean_records"]) == 2


def test_cphi_generation_pipeline_generates_only_missing_ids():
    csv_text = """identifier,sample_name
,sample_1
ABCD-123456,sample_2
"""

    result = run_generation_pipeline(
        file_bytes=to_bytes(csv_text),
        file_type="csv",
        strategy_name="CPHI",
        config={
            "project_code": "NRGI",
            "entity_type": "patient",
        },
        id_name="identifier",
    )

    assert result["mode"] == "generation"
    assert result["summary"]["total_rows"] == 2
    assert result["summary"]["generated_count"] == 1
    assert result["summary"]["skipped_count"] == 1
    assert result["summary"]["duplicate_count"] == 0
    assert result["summary"]["generation_conflict_count"] == 0
    assert result["summary"]["error_count"] == 0
    assert result["summary"]["clean_count"] == 2

    updated_records = result["updated_records"]

    generated_id = updated_records[0]["identifier"]

    assert re.fullmatch(r"NRGI-\d{6}", generated_id)
    assert updated_records[1]["identifier"] == "ABCD-123456"

    assert result["results"][0]["action"] == "generated"
    assert result["results"][0]["valid"] is True
    assert result["results"][1]["action"] == "skipped_existing_id"
    assert result["results"][1]["valid"] is True

    assert len(result["clean_records"]) == 2


def test_cphi_modifier_generation_pipeline():
    csv_text = """identifier,sample_name
,sample_1
"""

    result = run_generation_pipeline(
        file_bytes=to_bytes(csv_text),
        file_type="csv",
        strategy_name="CPHI",
        config={
            "project_code": "NRGI",
            "entity_type": "sample",
            "variant": "EXP",
        },
        id_name="identifier",
    )

    assert result["mode"] == "generation"
    assert result["summary"]["total_rows"] == 1
    assert result["summary"]["generated_count"] == 1
    assert result["summary"]["skipped_count"] == 0
    assert result["summary"]["duplicate_count"] == 0
    assert result["summary"]["generation_conflict_count"] == 0
    assert result["summary"]["error_count"] == 0
    assert result["summary"]["clean_count"] == 1

    generated_id = result["updated_records"][0]["identifier"]

    assert re.fullmatch(r"NRGI-\d{6}_EXP_\d{4}", generated_id)

    assert result["results"][0]["action"] == "generated"
    assert result["results"][0]["valid"] is True
    assert len(result["clean_records"]) == 1


def test_cphi_validation_pipeline_valid_and_invalid_rows():
    csv_text = """identifier,sample_name
NRGI-123456,sample_1
BAD_IDENTIFIER,sample_2
"""

    result = run_validation_pipeline(
        file_bytes=to_bytes(csv_text),
        file_type="csv",
        strategy_name="CPHI",
        config={
            "project_code": "NRGI",
            "entity_type": "patient",
        },
        id_name="identifier",
    )

    assert result["mode"] == "validation"
    assert result["summary"]["total_rows"] == 2
    assert result["summary"]["valid_count"] == 1
    assert result["summary"]["invalid_count"] == 1
    assert result["summary"]["duplicate_count"] == 0
    assert result["summary"]["clean_count"] == 1

    assert result["results"][0]["valid"] is True
    assert result["results"][1]["valid"] is False

    assert len(result["clean_records"]) == 1


def test_cphi_pipeline_missing_entity_type_raises_error():
    csv_text = """identifier,sample_name
NRGI-123456,sample_1
"""

    with pytest.raises(ValueError, match="Missing 'entity_type'"):
        run_validation_pipeline(
            file_bytes=to_bytes(csv_text),
            file_type="csv",
            strategy_name="CPHI",
            config={
                "project_code": "NRGI",
            },
            id_name="identifier",
        )


def test_uuid_validation_marks_both_duplicate_rows_invalid():
    duplicate_uuid = str(uuid.uuid4())

    csv_text = f"""uuid,sample_name
{duplicate_uuid},sample_1
{duplicate_uuid},sample_2
{str(uuid.uuid4())},sample_3
"""

    result = run_validation_pipeline(
        file_bytes=to_bytes(csv_text),
        file_type="csv",
        strategy_name="UUID",
        config={"version": 4},
        id_name="uuid",
    )

    assert result["mode"] == "validation"
    assert result["summary"]["total_rows"] == 3
    assert result["summary"]["valid_count"] == 1
    assert result["summary"]["invalid_count"] == 2
    assert result["summary"]["duplicate_count"] == 2
    assert result["summary"]["clean_count"] == 1

    assert result["results"][0]["valid"] is False
    assert result["results"][0]["error"] == "Duplicate identifier"
    assert result["results"][1]["valid"] is False
    assert result["results"][1]["error"] == "Duplicate identifier"

    assert result["results"][2]["valid"] is True


def test_cphi_validation_marks_both_duplicate_rows_invalid():
    csv_text = """identifier,sample_name
NRGI-123456,sample_1
NRGI-123456,sample_2
NRGI-654321,sample_3
"""

    result = run_validation_pipeline(
        file_bytes=to_bytes(csv_text),
        file_type="csv",
        strategy_name="CPHI",
        config={
            "project_code": "NRGI",
            "entity_type": "patient",
        },
        id_name="identifier",
    )

    assert result["mode"] == "validation"
    assert result["summary"]["total_rows"] == 3
    assert result["summary"]["valid_count"] == 1
    assert result["summary"]["invalid_count"] == 2
    assert result["summary"]["duplicate_count"] == 2
    assert result["summary"]["clean_count"] == 1

    assert result["results"][0]["valid"] is False
    assert result["results"][0]["error"] == "Duplicate identifier"
    assert result["results"][1]["valid"] is False
    assert result["results"][1]["error"] == "Duplicate identifier"

    assert result["results"][2]["valid"] is True


def test_generation_marks_existing_duplicate_rows_as_conflicts_but_generates_missing_rows():
    csv_text = """identifier,sample_name
NRGI-123456,sample_1
,sample_2
NRGI-123456,sample_3
"""

    result = run_generation_pipeline(
        file_bytes=to_bytes(csv_text),
        file_type="csv",
        strategy_name="CPHI",
        config={
            "project_code": "NRGI",
            "entity_type": "patient",
        },
        id_name="identifier",
    )

    assert result["mode"] == "generation"
    assert result["summary"]["total_rows"] == 3
    assert result["summary"]["generated_count"] == 1
    assert result["summary"]["skipped_count"] == 0
    assert result["summary"]["duplicate_count"] == 2
    assert result["summary"]["generation_conflict_count"] == 0
    assert result["summary"]["error_count"] == 0
    assert result["summary"]["clean_count"] == 1

    assert result["results"][0]["action"] == "duplicate_existing_id"
    assert result["results"][0]["valid"] is False
    assert result["results"][0]["error"] == "Duplicate identifier"

    assert result["results"][1]["action"] == "generated"
    assert result["results"][1]["valid"] is True
    assert re.fullmatch(r"NRGI-\d{6}", result["results"][1]["identifier"])

    assert result["results"][2]["action"] == "duplicate_existing_id"
    assert result["results"][2]["valid"] is False
    assert result["results"][2]["error"] == "Duplicate identifier"

    assert len(result["clean_records"]) == 1
    assert re.fullmatch(r"NRGI-\d{6}", result["clean_records"][0]["identifier"])


def test_generation_existing_invalid_id_is_not_clean():
    csv_text = """identifier,sample_name
BAD_IDENTIFIER,sample_1
,sample_2
"""

    result = run_generation_pipeline(
        file_bytes=to_bytes(csv_text),
        file_type="csv",
        strategy_name="CPHI",
        config={
            "project_code": "NRGI",
            "entity_type": "patient",
        },
        id_name="identifier",
    )

    assert result["mode"] == "generation"
    assert result["summary"]["total_rows"] == 2
    assert result["summary"]["generated_count"] == 1
    assert result["summary"]["skipped_count"] == 0
    assert result["summary"]["duplicate_count"] == 0
    assert result["summary"]["generation_conflict_count"] == 0
    assert result["summary"]["error_count"] == 1
    assert result["summary"]["clean_count"] == 1

    assert result["results"][0]["action"] == "existing_id_invalid"
    assert result["results"][0]["valid"] is False

    assert result["results"][1]["action"] == "generated"
    assert result["results"][1]["valid"] is True

    assert len(result["clean_records"]) == 1