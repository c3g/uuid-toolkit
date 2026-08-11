import json
import uuid

from fastapi.testclient import TestClient

from main import app


client = TestClient(app)


def make_csv_file(csv_text: str, filename: str = "test.csv"):
    """
    Helper for uploading CSV text as a file to FastAPI TestClient.
    """
    return {
        "file": (
            filename,
            csv_text.encode("utf-8-sig"),
            "text/csv",
        )
    }


def test_health_endpoint():
    response = client.get("/api/health")

    assert response.status_code == 200

    data = response.json()

    assert data["status"] == "ok"




def test_uuid_generate_endpoint():
    existing_uuid = str(uuid.uuid4())

    csv_text = f"""uuid,sample_name
,sample_1
{existing_uuid},sample_2
,sample_3
"""

    response = client.post(
        "/api/generate",
        data={
            "strategy_name": "UUID",
            "config_json": json.dumps({"version": 4}),
            "id_name": "uuid",
            "output_id_field": "uuid",
        },
        files=make_csv_file(csv_text, "uuid_generate.csv"),
    )

    assert response.status_code == 200

    data = response.json()

    assert data["mode"] == "generation"
    assert data["summary"]["total_rows"] == 3
    assert data["summary"]["generated_count"] == 2
    assert data["summary"]["skipped_count"] == 1

    updated_records = data["updated_records"]

    assert updated_records[1]["uuid"] == existing_uuid

    generated_1 = uuid.UUID(updated_records[0]["uuid"])
    generated_2 = uuid.UUID(updated_records[2]["uuid"])

    assert generated_1.version == 4
    assert generated_2.version == 4


def test_uuid_validate_endpoint():
    valid_uuid = str(uuid.uuid4())
    wrong_version_uuid = str(uuid.uuid1())

    csv_text = f"""uuid,sample_name
{valid_uuid},sample_1
not-a-uuid,sample_2
{wrong_version_uuid},sample_3
,sample_4
"""

    response = client.post(
        "/api/validate",
        data={
            "strategy_name": "UUID",
            "config_json": json.dumps({"version": 4}),
            "id_name": "uuid",
        },
        files=make_csv_file(csv_text, "uuid_validate.csv"),
    )

    assert response.status_code == 200

    data = response.json()

    assert data["mode"] == "validation"
    assert data["summary"]["total_rows"] == 4
    assert data["summary"]["valid_count"] == 1
    assert data["summary"]["invalid_count"] == 3

    assert data["results"][0]["valid"] is True
    assert data["results"][1]["error"] == "Invalid UUID format"
    assert data["results"][2]["error"] == "UUID version mismatch"
    assert data["results"][3]["error"] == "Missing identifier"


def test_cphi_generate_base_patient_endpoint():
    csv_text = """identifier,patient_name
,patient_1
NRGI-123456,patient_2
"""

    response = client.post(
        "/api/generate",
        data={
            "strategy_name": "CPHI",
            "config_json": json.dumps(
                {
                    "project_code": "NRGI",
                    "entity_type": "patient",
                }
            ),
            "id_name": "identifier",
            "output_id_field": "identifier",
        },
        files=make_csv_file(csv_text, "cphi_patient_generate.csv"),
    )

    assert response.status_code == 200

    data = response.json()

    assert data["mode"] == "generation"
    assert data["summary"]["total_rows"] == 2
    assert data["summary"]["generated_count"] == 1
    assert data["summary"]["skipped_count"] == 1

    generated_id = data["updated_records"][0]["identifier"]
    existing_id = data["updated_records"][1]["identifier"]

    assert generated_id.startswith("NRGI-")
    assert len(generated_id) == len("NRGI-123456")
    assert generated_id[5:].isdigit()

    assert existing_id == "NRGI-123456"


def test_cphi_generate_sample_variant_endpoint():
    csv_text = """identifier,sample_name
,sample_1
NRGI-123456_EXP_0001,sample_2
"""

    response = client.post(
        "/api/generate",
        data={
            "strategy_name": "CPHI",
            "config_json": json.dumps(
                {
                    "project_code": "NRGI",
                    "entity_type": "sample",
                    "variant": "EXP",
                }
            ),
            "id_name": "identifier",
            "output_id_field": "identifier",
        },
        files=make_csv_file(csv_text, "cphi_sample_exp_generate.csv"),
    )

    assert response.status_code == 200

    data = response.json()

    assert data["mode"] == "generation"
    assert data["summary"]["generated_count"] == 1
    assert data["summary"]["skipped_count"] == 1

    generated_id = data["updated_records"][0]["identifier"]

    assert generated_id.startswith("NRGI-")
    assert "_EXP_" in generated_id

    base_part, modifier_part = generated_id.split("_EXP_")

    assert len(base_part) == len("NRGI-123456")
    assert base_part.startswith("NRGI-")
    assert base_part[5:].isdigit()

    assert len(modifier_part) == 4
    assert modifier_part.isdigit()


def test_cphi_validate_sample_variant_endpoint():
    csv_text = """identifier,sample_name
NRGI-123456_EXP_0001,sample_1
NRGI-123456_RG_0001,sample_2
NRGI-ABC123_EXP_0001,sample_3
,sample_4
"""

    response = client.post(
        "/api/validate",
        data={
            "strategy_name": "CPHI",
            "config_json": json.dumps(
                {
                    "project_code": "NRGI",
                    "entity_type": "sample",
                    "variant": "EXP",
                }
            ),
            "id_name": "identifier",
        },
        files=make_csv_file(csv_text, "cphi_sample_exp_validate.csv"),
    )

    assert response.status_code == 200

    data = response.json()

    assert data["mode"] == "validation"
    assert data["summary"]["total_rows"] == 4
    assert data["summary"]["valid_count"] == 1
    assert data["summary"]["invalid_count"] == 3

    assert data["results"][0]["valid"] is True
    assert data["results"][1]["valid"] is False
    assert data["results"][2]["valid"] is False
    assert data["results"][3]["error"] == "Missing identifier"


def test_invalid_cphi_patient_variant_returns_400():
    csv_text = """identifier,patient_name
,patient_1
"""

    response = client.post(
        "/api/generate",
        data={
            "strategy_name": "CPHI",
            "config_json": json.dumps(
                {
                    "project_code": "NRGI",
                    "entity_type": "patient",
                    "variant": "EXP",
                }
            ),
            "id_name": "identifier",
            "output_id_field": "identifier",
        },
        files=make_csv_file(csv_text, "invalid_cphi_config.csv"),
    )

    assert response.status_code == 400

    data = response.json()

    assert "not allowed for entity_type 'patient'" in data["detail"]


def test_missing_cphi_entity_type_returns_400():
    csv_text = """identifier,name
,sample_1
"""

    response = client.post(
        "/api/generate",
        data={
            "strategy_name": "CPHI",
            "config_json": json.dumps(
                {
                    "project_code": "NRGI",
                }
            ),
            "id_name": "identifier",
            "output_id_field": "identifier",
        },
        files=make_csv_file(csv_text, "missing_entity_type.csv"),
    )

    assert response.status_code == 400

    data = response.json()

    assert "entity_type is required" in data["detail"]