import re
import uuid

from core.pipeline import run_generation_pipeline


def to_bytes(text: str) -> bytes:
    return text.encode("utf-8")


# ------------------------------------------------------------------
# UUID fill-missing generation
# ------------------------------------------------------------------


def test_uuid_generation_generates_missing_and_preserves_existing():
    existing_uuid = str(uuid.uuid4())

    csv_text = f"""identifier,name
,sample_1
{existing_uuid},sample_2
"""

    result = run_generation_pipeline(
        file_bytes=to_bytes(csv_text),
        file_type="csv",
        strategy_name="UUID",
        config={"version": 4},
        id_name="identifier",
    )

    assert result["mode"] == "generation"

    summary = result["summary"]

    assert summary["total_rows"] == 2
    assert summary["existing_count"] == 1
    assert summary["missing_count"] == 1
    assert summary["generated_count"] == 1
    assert summary["skipped_count"] == 1
    assert summary["error_count"] == 0
    assert summary["clean_count"] == 2

    generated_uuid = result["updated_records"][0]["identifier"]

    parsed_uuid = uuid.UUID(generated_uuid)

    assert parsed_uuid.version == 4

    assert (
        result["updated_records"][1]["identifier"]
        == existing_uuid
    )

    assert result["results"][0]["action"] == "generated"
    assert (
        result["results"][1]["action"]
        == "skipped_existing_id"
    )


# ------------------------------------------------------------------
# CPHI fill-missing generation
# ------------------------------------------------------------------


def test_cphi_generation_generates_missing_identifier():
    csv_text = """identifier,name
,sample_1
"""

    result = run_generation_pipeline(
        file_bytes=to_bytes(csv_text),
        file_type="csv",
        strategy_name="CPHI",
        config={
            "project_code": "NRGI",
            "entity_type": "sample",
        },
        id_name="identifier",
    )

    assert result["summary"]["generated_count"] == 1
    assert result["summary"]["clean_count"] == 1

    generated = result["updated_records"][0]["identifier"]

    assert re.fullmatch(
        r"NRGI-\d{6}",
        generated,
    )

    assert result["results"][0]["action"] == "generated"
    assert result["results"][0]["valid"] is True


def test_cphi_generation_preserves_valid_existing_identifier():
    csv_text = """identifier,name
NRGI-654321,sample_1
"""

    result = run_generation_pipeline(
        file_bytes=to_bytes(csv_text),
        file_type="csv",
        strategy_name="CPHI",
        config={
            "project_code": "NRGI",
            "entity_type": "sample",
        },
        id_name="identifier",
    )

    assert result["summary"]["generated_count"] == 0
    assert result["summary"]["skipped_count"] == 1
    assert result["summary"]["clean_count"] == 1

    assert (
        result["updated_records"][0]["identifier"]
        == "NRGI-654321"
    )

    assert (
        result["results"][0]["action"]
        == "skipped_existing_id"
    )


def test_cphi_generation_does_not_replace_invalid_existing_identifier():
    csv_text = """identifier,name
BAD_IDENTIFIER,sample_1
,sample_2
"""

    result = run_generation_pipeline(
        file_bytes=to_bytes(csv_text),
        file_type="csv",
        strategy_name="CPHI",
        config={
            "project_code": "NRGI",
            "entity_type": "sample",
        },
        id_name="identifier",
    )

    assert result["summary"]["total_rows"] == 2
    assert result["summary"]["generated_count"] == 1
    assert result["summary"]["error_count"] == 1
    assert result["summary"]["clean_count"] == 1

    assert (
        result["results"][0]["action"]
        == "existing_id_invalid"
    )
    assert result["results"][0]["valid"] is False

    # Original invalid ID remains unchanged.
    assert (
        result["updated_records"][0]["identifier"]
        == "BAD_IDENTIFIER"
    )

    generated = result["updated_records"][1]["identifier"]

    assert re.fullmatch(r"NRGI-\d{6}", generated)


def test_cphi_generation_marks_duplicate_existing_identifiers_invalid():
    csv_text = """identifier,name
NRGI-123456,sample_1
NRGI-123456,sample_2
,sample_3
"""

    result = run_generation_pipeline(
        file_bytes=to_bytes(csv_text),
        file_type="csv",
        strategy_name="CPHI",
        config={
            "project_code": "NRGI",
            "entity_type": "sample",
        },
        id_name="identifier",
    )

    assert result["summary"]["duplicate_count"] == 2
    assert result["summary"]["generated_count"] == 1
    assert result["summary"]["clean_count"] == 1

    assert (
        result["results"][0]["action"]
        == "duplicate_existing_id"
    )
    assert (
        result["results"][1]["action"]
        == "duplicate_existing_id"
    )

    assert result["results"][0]["valid"] is False
    assert result["results"][1]["valid"] is False

    assert result["results"][2]["action"] == "generated"
    assert result["results"][2]["valid"] is True


# ------------------------------------------------------------------
# Reserved identifier conflict handling
# ------------------------------------------------------------------


def test_cphi_generation_avoids_reserved_identifier(
    monkeypatch,
):
    generated_values = iter(
        [
            "NRGI-999999",
            "NRGI-123456",
        ]
    )

    def fake_generate(self, config):
        return next(generated_values)

    monkeypatch.setattr(
        "strategies.cphi.CPHIStrategy.generate",
        fake_generate,
    )

    csv_text = """identifier,name
,sample_1
"""

    result = run_generation_pipeline(
        file_bytes=to_bytes(csv_text),
        file_type="csv",
        strategy_name="CPHI",
        config={
            "project_code": "NRGI",
            "entity_type": "sample",
        },
        id_name="identifier",
        reserved_identifiers={
            "NRGI-999999",
        },
    )

    assert result["summary"]["generated_count"] == 1
    assert result["summary"]["generation_conflict_count"] == 0

    assert (
        result["results"][0]["identifier"]
        == "NRGI-123456"
    )


# ------------------------------------------------------------------
# PCGL derived generation
# ------------------------------------------------------------------


def test_pcgl_generation_derives_multiple_variants():
    csv_text = """identifier,name
NRGI-123456,sample_1
NRGI-654321,sample_2
"""

    result = run_generation_pipeline(
        file_bytes=to_bytes(csv_text),
        file_type="csv",
        strategy_name="PCGL",
        config={
            "project_code": "NRGI",
            "entity_type": "sample",
            "variants": [
                "EXP",
                "LIB",
            ],
        },
        id_name="identifier",
        output_id_field="identifier",
    )

    assert result["mode"] == "generation"
    assert (
        result["generation_mode"]
        == "derive_from_existing"
    )

    summary = result["summary"]

    assert summary["total_rows"] == 2
    assert summary["generated_row_count"] == 2
    assert summary["generated_identifier_count"] == 4
    assert summary["missing_source_count"] == 0
    assert summary["duplicate_source_count"] == 0
    assert summary["source_invalid_count"] == 0
    assert summary["generation_conflict_count"] == 0
    assert summary["error_count"] == 0
    assert summary["clean_count"] == 2

    first = result["updated_records"][0]
    second = result["updated_records"][1]

    assert re.fullmatch(
        r"NRGI-123456_EXP_\d{4}",
        first["identifier_EXP"],
    )

    assert re.fullmatch(
        r"NRGI-123456_LIB_\d{4}",
        first["identifier_LIB"],
    )

    assert re.fullmatch(
        r"NRGI-654321_EXP_\d{4}",
        second["identifier_EXP"],
    )

    assert re.fullmatch(
        r"NRGI-654321_LIB_\d{4}",
        second["identifier_LIB"],
    )

    assert all(
        row["action"] == "derived_generated"
        for row in result["results"]
    )


def test_pcgl_derived_generation_requires_source_identifier():
    csv_text = """identifier,name
,sample_1
"""

    result = run_generation_pipeline(
        file_bytes=to_bytes(csv_text),
        file_type="csv",
        strategy_name="PCGL",
        config={
            "project_code": "NRGI",
            "entity_type": "sample",
            "variants": ["EXP"],
        },
        id_name="identifier",
    )

    assert result["summary"]["generated_row_count"] == 0
    assert result["summary"]["missing_source_count"] == 1
    assert result["summary"]["error_count"] == 1
    assert result["summary"]["clean_count"] == 0

    row = result["results"][0]

    assert row["action"] == "source_id_missing"
    assert row["valid"] is False
    assert row["error"] == "Missing source identifier"


def test_pcgl_derived_generation_rejects_invalid_source():
    csv_text = """identifier,name
BAD_IDENTIFIER,sample_1
"""

    result = run_generation_pipeline(
        file_bytes=to_bytes(csv_text),
        file_type="csv",
        strategy_name="PCGL",
        config={
            "project_code": "NRGI",
            "entity_type": "sample",
            "variants": ["EXP"],
        },
        id_name="identifier",
    )

    assert result["summary"]["source_invalid_count"] == 1
    assert result["summary"]["generated_row_count"] == 0
    assert result["summary"]["clean_count"] == 0

    row = result["results"][0]

    assert row["action"] == "source_id_invalid"
    assert row["valid"] is False
    assert row["error"] == "Invalid source identifier"


def test_pcgl_derived_generation_rejects_duplicate_sources():
    csv_text = """identifier,name
NRGI-123456,sample_1
NRGI-123456,sample_2
"""

    result = run_generation_pipeline(
        file_bytes=to_bytes(csv_text),
        file_type="csv",
        strategy_name="PCGL",
        config={
            "project_code": "NRGI",
            "entity_type": "sample",
            "variants": ["EXP"],
        },
        id_name="identifier",
    )

    assert result["summary"]["duplicate_source_count"] == 2
    assert result["summary"]["generated_row_count"] == 0
    assert result["summary"]["clean_count"] == 0
    assert result["summary"]["error_count"] == 2

    assert all(
        row["action"] == "duplicate_source_id"
        for row in result["results"]
    )

    assert all(
        row["valid"] is False
        for row in result["results"]
    )