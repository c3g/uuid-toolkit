import uuid

from core.pipeline import run_validation_pipeline


def to_bytes(text: str) -> bytes:
    return text.encode("utf-8")


# ------------------------------------------------------------------
# UUID validation
# ------------------------------------------------------------------


def test_uuid_validation_accepts_valid_uuid_and_rejects_invalid_uuid():
    valid_uuid = str(uuid.uuid4())

    csv_text = f"""identifier,name
{valid_uuid},sample_1
not-a-uuid,sample_2
"""

    result = run_validation_pipeline(
        file_bytes=to_bytes(csv_text),
        file_type="csv",
        strategy_name="UUID",
        config={"version": 4},
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

    assert len(result["updated_records"]) == 2
    assert len(result["clean_records"]) == 1


def test_uuid_validation_marks_all_duplicate_rows_invalid():
    duplicate_uuid = str(uuid.uuid4())
    unique_uuid = str(uuid.uuid4())

    csv_text = f"""identifier,name
{duplicate_uuid},sample_1
{duplicate_uuid},sample_2
{unique_uuid},sample_3
"""

    result = run_validation_pipeline(
        file_bytes=to_bytes(csv_text),
        file_type="csv",
        strategy_name="UUID",
        config={"version": 4},
        id_name="identifier",
    )

    assert result["summary"]["total_rows"] == 3
    assert result["summary"]["valid_count"] == 1
    assert result["summary"]["invalid_count"] == 2
    assert result["summary"]["duplicate_count"] == 2
    assert result["summary"]["clean_count"] == 1

    assert result["results"][0]["valid"] is False
    assert result["results"][1]["valid"] is False
    assert result["results"][2]["valid"] is True

    assert result["results"][0]["error"] == "Duplicate identifier"
    assert result["results"][1]["error"] == "Duplicate identifier"


# ------------------------------------------------------------------
# CPHI validation
# ------------------------------------------------------------------


def test_cphi_validation_accepts_valid_identifier():
    csv_text = """identifier,name
NRGI-123456,sample_1
"""

    result = run_validation_pipeline(
        file_bytes=to_bytes(csv_text),
        file_type="csv",
        strategy_name="CPHI",
        config={
            "project_code": "NRGI",
            "entity_type": "sample",
        },
        id_name="identifier",
    )

    assert result["summary"]["total_rows"] == 1
    assert result["summary"]["valid_count"] == 1
    assert result["summary"]["invalid_count"] == 0
    assert result["summary"]["clean_count"] == 1

    assert result["results"][0]["identifier"] == "NRGI-123456"
    assert result["results"][0]["valid"] is True


def test_cphi_validation_rejects_invalid_identifier():
    csv_text = """identifier,name
BAD_IDENTIFIER,sample_1
"""

    result = run_validation_pipeline(
        file_bytes=to_bytes(csv_text),
        file_type="csv",
        strategy_name="CPHI",
        config={
            "project_code": "NRGI",
            "entity_type": "sample",
        },
        id_name="identifier",
    )

    assert result["summary"]["valid_count"] == 0
    assert result["summary"]["invalid_count"] == 1
    assert result["summary"]["clean_count"] == 0

    assert result["results"][0]["valid"] is False


def test_cphi_validation_detects_duplicate_identifiers():
    csv_text = """identifier,name
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
            "entity_type": "sample",
        },
        id_name="identifier",
    )

    assert result["summary"]["duplicate_count"] == 2
    assert result["summary"]["valid_count"] == 1
    assert result["summary"]["invalid_count"] == 2

    assert result["results"][0]["error"] == "Duplicate identifier"
    assert result["results"][1]["error"] == "Duplicate identifier"
    assert result["results"][2]["valid"] is True


# ------------------------------------------------------------------
# PCGL validation
# ------------------------------------------------------------------


def test_pcgl_validation_accepts_matching_sample_variant():
    csv_text = """identifier,name
NRGI-123456_EXP_0001,sample_1
"""

    result = run_validation_pipeline(
        file_bytes=to_bytes(csv_text),
        file_type="csv",
        strategy_name="PCGL",
        config={
            "project_code": "NRGI",
            "entity_type": "sample",
            "variant": "EXP",
        },
        id_name="identifier",
    )

    assert result["summary"]["valid_count"] == 1
    assert result["summary"]["invalid_count"] == 0

    assert result["results"][0]["valid"] is True


def test_pcgl_validation_rejects_wrong_variant():
    csv_text = """identifier,name
NRGI-123456_RG_0001,sample_1
"""

    result = run_validation_pipeline(
        file_bytes=to_bytes(csv_text),
        file_type="csv",
        strategy_name="PCGL",
        config={
            "project_code": "NRGI",
            "entity_type": "sample",
            "variant": "EXP",
        },
        id_name="identifier",
    )

    assert result["summary"]["valid_count"] == 0
    assert result["summary"]["invalid_count"] == 1

    assert result["results"][0]["valid"] is False


def test_pcgl_validation_accepts_patient_spe_variant():
    csv_text = """identifier,name
NRGI-123456_SPE_0001,patient_1
"""

    result = run_validation_pipeline(
        file_bytes=to_bytes(csv_text),
        file_type="csv",
        strategy_name="PCGL",
        config={
            "project_code": "NRGI",
            "entity_type": "patient",
            "variant": "SPE",
        },
        id_name="identifier",
    )

    assert result["summary"]["valid_count"] == 1
    assert result["results"][0]["valid"] is True


def test_pcgl_validation_detects_duplicate_variant_identifiers():
    csv_text = """identifier,name
NRGI-123456_EXP_0001,sample_1
NRGI-123456_EXP_0001,sample_2
"""

    result = run_validation_pipeline(
        file_bytes=to_bytes(csv_text),
        file_type="csv",
        strategy_name="PCGL",
        config={
            "project_code": "NRGI",
            "entity_type": "sample",
            "variant": "EXP",
        },
        id_name="identifier",
    )

    assert result["summary"]["duplicate_count"] == 2
    assert result["summary"]["valid_count"] == 0
    assert result["summary"]["invalid_count"] == 2

    assert all(
        row["error"] == "Duplicate identifier"
        for row in result["results"]
    )