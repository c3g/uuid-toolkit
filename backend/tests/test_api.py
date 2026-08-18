import json
import uuid


def make_csv_file(
    text: str,
    filename: str = "test.csv",
):
    return {
        "file": (
            filename,
            text.encode("utf-8"),
            "text/csv",
        )
    }


def create_project(
    client,
    *,
    name: str,
    strategy_name: str,
):
    response = client.post(
        "/api/database-management/projects",
        data={
            "name": name,
            "strategy_name": strategy_name,
            "description": "API test project",
        },
    )

    assert response.status_code == 200

    return response.json()


def save_identifiers(
    client,
    *,
    strategy_name: str,
    project_id: int | None,
    identifiers: list[str],
):
    response = client.post(
        "/api/identifier_database/save",
        json={
            "strategy_name": strategy_name,
            "project_id": project_id,
            "identifiers": identifiers,
        },
    )

    assert response.status_code == 200

    return response.json()


# ------------------------------------------------------------------
# Health / readiness
# ------------------------------------------------------------------


def test_health_endpoint(client):
    response = client.get("/api/health")

    assert response.status_code == 200

    data = response.json()

    assert data["status"] == "ok"


def test_readiness_endpoint(client):
    response = client.get("/api/ready")

    assert response.status_code == 200

    data = response.json()

    assert data["status"] == "ready"


def test_unknown_api_endpoint_returns_404(client):
    response = client.get(
        "/api/this-endpoint-does-not-exist"
    )

    assert response.status_code == 404


# ------------------------------------------------------------------
# Validation API
# ------------------------------------------------------------------


def test_uuid_validation_endpoint(client):
    valid_uuid = str(uuid.uuid4())

    csv_text = f"""identifier,name
{valid_uuid},sample_1
not-a-uuid,sample_2
"""

    response = client.post(
        "/api/validate",
        data={
            "strategy_name": "UUID",
            "config_json": json.dumps(
                {"version": 4}
            ),
            "id_name": "identifier",
        },
        files=make_csv_file(csv_text),
    )

    assert response.status_code == 200

    data = response.json()

    assert data["mode"] == "validation"

    assert data["summary"]["total_rows"] == 2
    assert data["summary"]["valid_count"] == 1
    assert data["summary"]["invalid_count"] == 1

    assert (
        data["summary"]["database_hard_conflict_count"]
        == 0
    )


def test_cphi_validation_endpoint(client):
    csv_text = """identifier,name
NRGI-123456,sample_1
"""

    response = client.post(
        "/api/validate",
        data={
            "strategy_name": "CPHI",
            "config_json": json.dumps(
                {
                    "project_code": "NRGI",
                    "entity_type": "sample",
                }
            ),
            "id_name": "identifier",
        },
        files=make_csv_file(csv_text),
    )

    assert response.status_code == 200

    data = response.json()

    assert data["summary"]["valid_count"] == 1
    assert data["results"][0]["valid"] is True


def test_cphi_api_defaults_missing_entity_type_to_sample(
    client,
):
    csv_text = """identifier,name
NRGI-123456,sample_1
"""

    response = client.post(
        "/api/validate",
        data={
            "strategy_name": "CPHI",
            "config_json": json.dumps(
                {
                    "project_code": "NRGI",
                }
            ),
            "id_name": "identifier",
        },
        files=make_csv_file(csv_text),
    )

    assert response.status_code == 200

    data = response.json()

    assert data["summary"]["valid_count"] == 1


def test_pcgl_validation_endpoint(client):
    csv_text = """identifier,name
NRGI-123456_EXP_0001,sample_1
"""

    response = client.post(
        "/api/validate",
        data={
            "strategy_name": "PCGL",
            "config_json": json.dumps(
                {
                    "project_code": "NRGI",
                    "entity_type": "sample",
                    "variant": "EXP",
                }
            ),
            "id_name": "identifier",
        },
        files=make_csv_file(csv_text),
    )

    assert response.status_code == 200

    data = response.json()

    assert data["summary"]["valid_count"] == 1
    assert data["results"][0]["valid"] is True


def test_invalid_strategy_returns_400(client):
    csv_text = """identifier,name
something,sample_1
"""

    response = client.post(
        "/api/validate",
        data={
            "strategy_name": "NOT_A_STRATEGY",
            "config_json": "{}",
            "id_name": "identifier",
        },
        files=make_csv_file(csv_text),
    )

    assert response.status_code == 400


def test_invalid_config_json_returns_400(client):
    csv_text = """identifier,name
NRGI-123456,sample_1
"""

    response = client.post(
        "/api/validate",
        data={
            "strategy_name": "CPHI",
            "config_json": "{not valid json}",
            "id_name": "identifier",
        },
        files=make_csv_file(csv_text),
    )

    assert response.status_code == 400


# ------------------------------------------------------------------
# Generation API
# ------------------------------------------------------------------


def test_uuid_generation_endpoint(client):
    csv_text = """identifier,name
,sample_1
"""

    response = client.post(
        "/api/generate",
        data={
            "strategy_name": "UUID",
            "config_json": json.dumps(
                {"version": 4}
            ),
            "id_name": "identifier",
            "output_id_field": "identifier",
        },
        files=make_csv_file(csv_text),
    )

    assert response.status_code == 200

    data = response.json()

    assert data["mode"] == "generation"
    assert data["summary"]["generated_count"] == 1
    assert data["summary"]["valid_count"] == 1

    generated = data["results"][0]["identifier"]

    parsed = uuid.UUID(generated)

    assert parsed.version == 4


def test_cphi_generation_endpoint(client):
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
                    "entity_type": "sample",
                }
            ),
            "id_name": "identifier",
            "output_id_field": "identifier",
        },
        files=make_csv_file(csv_text),
    )

    assert response.status_code == 200

    data = response.json()

    assert data["summary"]["generated_count"] == 1
    assert data["summary"]["valid_count"] == 1
    assert data["results"][0]["action"] == "generated"


def test_pcgl_derived_generation_endpoint(client):
    csv_text = """identifier,name
NRGI-123456,sample_1
"""

    response = client.post(
        "/api/generate",
        data={
            "strategy_name": "PCGL",
            "config_json": json.dumps(
                {
                    "project_code": "NRGI",
                    "entity_type": "sample",
                    "variants": [
                        "EXP",
                        "LIB",
                    ],
                }
            ),
            "id_name": "identifier",
            "output_id_field": "identifier",
        },
        files=make_csv_file(csv_text),
    )

    assert response.status_code == 200

    data = response.json()

    assert (
        data["generation_mode"]
        == "derive_from_existing"
    )

    assert (
        data["summary"]["generated_identifier_count"]
        == 2
    )

    generated = (
        data["results"][0]["generated_identifiers"]
    )

    assert "identifier_EXP" in generated
    assert "identifier_LIB" in generated


# ------------------------------------------------------------------
# Project / identifier database API
# ------------------------------------------------------------------


def test_create_project_save_identifier_and_read_it(
    client,
):
    project = create_project(
        client,
        name="API Project",
        strategy_name="CPHI",
    )

    save_result = save_identifiers(
        client,
        strategy_name="CPHI",
        project_id=project["id"],
        identifiers=[
            "NRGI-111111",
            "NRGI-222222",
        ],
    )

    assert save_result["saved_count"] == 2
    assert save_result["already_in_project_count"] == 0

    response = client.get(
        "/api/identifier_database",
        params={
            "project_id": project["id"],
        },
    )

    assert response.status_code == 200

    records = response.json()

    assert len(records) == 2

    values = {
        record["identifier_value"]
        for record in records
    }

    assert values == {
        "NRGI-111111",
        "NRGI-222222",
    }


def test_saving_without_project_uses_unassigned(
    client,
):
    result = save_identifiers(
        client,
        strategy_name="CPHI",
        project_id=None,
        identifiers=["NRGI-111111"],
    )

    assert result["project_name"] == "Unassigned"
    assert result["strategy_name"] == "CPHI"
    assert result["saved_count"] == 1


def test_resaving_identifier_skips_existing_identifier(
    client,
):
    project = create_project(
        client,
        name="API Project",
        strategy_name="CPHI",
    )

    save_identifiers(
        client,
        strategy_name="CPHI",
        project_id=project["id"],
        identifiers=["NRGI-111111"],
    )

    second = save_identifiers(
        client,
        strategy_name="CPHI",
        project_id=project["id"],
        identifiers=["NRGI-111111"],
    )

    assert second["saved_count"] == 0
    assert second["already_in_project_count"] == 1

    assert second["already_in_project_identifiers"] == [
        "NRGI-111111"
    ]


def test_save_rejects_project_strategy_mismatch(
    client,
):
    project = create_project(
        client,
        name="CPHI Project",
        strategy_name="CPHI",
    )

    response = client.post(
        "/api/identifier_database/save",
        json={
            "strategy_name": "PCGL",
            "project_id": project["id"],
            "identifiers": [
                "NRGI-111111_EXP_0001"
            ],
        },
    )

    assert response.status_code == 400


# ------------------------------------------------------------------
# Database comparison through API
# ------------------------------------------------------------------


def test_validation_marks_selected_project_match_as_hard_conflict(
    client,
):
    project = create_project(
        client,
        name="Project A",
        strategy_name="CPHI",
    )

    save_identifiers(
        client,
        strategy_name="CPHI",
        project_id=project["id"],
        identifiers=["NRGI-111111"],
    )

    csv_text = """identifier,name
NRGI-111111,sample_1
"""

    response = client.post(
        "/api/validate",
        data={
            "strategy_name": "CPHI",
            "config_json": json.dumps(
                {
                    "project_code": "NRGI",
                    "entity_type": "sample",
                }
            ),
            "id_name": "identifier",
            "project_id": str(project["id"]),
        },
        files=make_csv_file(csv_text),
    )

    assert response.status_code == 200

    data = response.json()

    row = data["results"][0]

    assert row["valid"] is False
    assert row["error"] == "Database conflict"

    assert (
        data["summary"]["database_hard_conflict_count"]
        == 1
    )

    assert data["summary"]["clean_count"] == 0


def test_validation_other_project_match_is_soft_warning(
    client,
):
    selected_project = create_project(
        client,
        name="Project A",
        strategy_name="CPHI",
    )

    other_project = create_project(
        client,
        name="Project B",
        strategy_name="CPHI",
    )

    save_identifiers(
        client,
        strategy_name="CPHI",
        project_id=other_project["id"],
        identifiers=["NRGI-222222"],
    )

    csv_text = """identifier,name
NRGI-222222,sample_1
"""

    response = client.post(
        "/api/validate",
        data={
            "strategy_name": "CPHI",
            "config_json": json.dumps(
                {
                    "project_code": "NRGI",
                    "entity_type": "sample",
                }
            ),
            "id_name": "identifier",
            "project_id": str(
                selected_project["id"]
            ),
        },
        files=make_csv_file(csv_text),
    )

    assert response.status_code == 200

    data = response.json()

    row = data["results"][0]

    assert row["valid"] is True
    assert row["error"] is None

    assert "Warning:" in row["message"]
    assert "Project B" in row["message"]

    assert (
        data["summary"]["database_hard_conflict_count"]
        == 0
    )

    assert (
        data["summary"]["database_soft_warning_count"]
        == 1
    )

    assert data["summary"]["clean_count"] == 1


def test_validation_without_project_uses_strategy_wide_hard_conflict(
    client,
):
    project = create_project(
        client,
        name="Project A",
        strategy_name="CPHI",
    )

    save_identifiers(
        client,
        strategy_name="CPHI",
        project_id=project["id"],
        identifiers=["NRGI-333333"],
    )

    csv_text = """identifier,name
NRGI-333333,sample_1
"""

    response = client.post(
        "/api/validate",
        data={
            "strategy_name": "CPHI",
            "config_json": json.dumps(
                {
                    "project_code": "NRGI",
                    "entity_type": "sample",
                }
            ),
            "id_name": "identifier",
        },
        files=make_csv_file(csv_text),
    )

    assert response.status_code == 200

    data = response.json()

    assert data["results"][0]["valid"] is False
    assert (
        data["results"][0]["error"]
        == "Database conflict"
    )

    assert (
        data["summary"]["database_hard_conflict_count"]
        == 1
    )

    assert (
        data["summary"]["database_soft_warning_count"]
        == 0
    )