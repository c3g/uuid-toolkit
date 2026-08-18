import pytest

from db.comparison import (
    compare_identifiers_to_database,
    get_hard_reserved_identifiers_for_generation,
    resolve_database_scope,
)
from db.database_management import create_project
from db.identifier_repository import (
    find_other_project_matches,
    find_project_conflicts,
    find_strategy_conflicts,
    list_identifiers,
    list_identifiers_by_project,
    list_identifiers_by_strategy,
    save_identifiers_to_project,
)
from db.project_repository import (
    get_or_create_unassigned_project,
)


def make_project(
    session,
    *,
    name: str,
    strategy_name: str,
):
    return create_project(
        session,
        name=name,
        strategy_name=strategy_name,
        description="Test project",
    )


# ------------------------------------------------------------------
# Projects
# ------------------------------------------------------------------


def test_create_project(db_session):
    project = make_project(
        db_session,
        name="Project A",
        strategy_name="CPHI",
    )

    assert project.id is not None
    assert project.name == "Project A"
    assert project.strategy_name == "CPHI"


def test_same_project_name_allowed_under_different_strategies(
    db_session,
):
    cphi_project = make_project(
        db_session,
        name="Shared Name",
        strategy_name="CPHI",
    )

    pcgl_project = make_project(
        db_session,
        name="Shared Name",
        strategy_name="PCGL",
    )

    assert cphi_project.id != pcgl_project.id
    assert cphi_project.name == pcgl_project.name

    assert cphi_project.strategy_name == "CPHI"
    assert pcgl_project.strategy_name == "PCGL"


def test_duplicate_project_name_same_strategy_is_rejected(
    db_session,
):
    make_project(
        db_session,
        name="Project A",
        strategy_name="CPHI",
    )

    with pytest.raises(ValueError):
        make_project(
            db_session,
            name="Project A",
            strategy_name="CPHI",
        )


def test_unassigned_project_is_strategy_specific(
    db_session,
):
    cphi_unassigned = get_or_create_unassigned_project(
        db_session,
        strategy_name="CPHI",
    )

    pcgl_unassigned = get_or_create_unassigned_project(
        db_session,
        strategy_name="PCGL",
    )

    assert cphi_unassigned.name == "Unassigned"
    assert pcgl_unassigned.name == "Unassigned"

    assert cphi_unassigned.strategy_name == "CPHI"
    assert pcgl_unassigned.strategy_name == "PCGL"

    assert cphi_unassigned.id != pcgl_unassigned.id


def test_get_or_create_unassigned_returns_existing_project(
    db_session,
):
    first = get_or_create_unassigned_project(
        db_session,
        strategy_name="CPHI",
    )

    second = get_or_create_unassigned_project(
        db_session,
        strategy_name="CPHI",
    )

    assert first.id == second.id


# ------------------------------------------------------------------
# Identifier repository
# ------------------------------------------------------------------


def test_save_and_list_identifiers(db_session):
    project = make_project(
        db_session,
        name="Project A",
        strategy_name="CPHI",
    )

    saved = save_identifiers_to_project(
        db_session,
        project_id=project.id,
        strategy_name="CPHI",
        identifiers={
            "NRGI-111111",
            "NRGI-222222",
        },
    )

    assert len(saved) == 2

    all_identifiers = list_identifiers(db_session)

    assert len(all_identifiers) == 2

    values = {
        record.identifier_value
        for record in all_identifiers
    }

    assert values == {
        "NRGI-111111",
        "NRGI-222222",
    }


def test_list_identifiers_by_project(db_session):
    project_a = make_project(
        db_session,
        name="Project A",
        strategy_name="CPHI",
    )

    project_b = make_project(
        db_session,
        name="Project B",
        strategy_name="CPHI",
    )

    save_identifiers_to_project(
        db_session,
        project_id=project_a.id,
        strategy_name="CPHI",
        identifiers={"NRGI-111111"},
    )

    save_identifiers_to_project(
        db_session,
        project_id=project_b.id,
        strategy_name="CPHI",
        identifiers={"NRGI-222222"},
    )

    records = list_identifiers_by_project(
        db_session,
        project_id=project_a.id,
    )

    assert len(records) == 1
    assert records[0].identifier_value == "NRGI-111111"


def test_list_identifiers_by_strategy(db_session):
    cphi_project = make_project(
        db_session,
        name="CPHI Project",
        strategy_name="CPHI",
    )

    pcgl_project = make_project(
        db_session,
        name="PCGL Project",
        strategy_name="PCGL",
    )

    save_identifiers_to_project(
        db_session,
        project_id=cphi_project.id,
        strategy_name="CPHI",
        identifiers={"NRGI-111111"},
    )

    save_identifiers_to_project(
        db_session,
        project_id=pcgl_project.id,
        strategy_name="PCGL",
        identifiers={"NRGI-222222_EXP_0001"},
    )

    records = list_identifiers_by_strategy(
        db_session,
        strategy_name="CPHI",
    )

    assert len(records) == 1
    assert records[0].identifier_value == "NRGI-111111"
    assert records[0].strategy_name == "CPHI"


def test_duplicate_identifier_inside_same_project_is_rejected(
    db_session,
):
    project = make_project(
        db_session,
        name="Project A",
        strategy_name="CPHI",
    )

    save_identifiers_to_project(
        db_session,
        project_id=project.id,
        strategy_name="CPHI",
        identifiers={"NRGI-111111"},
    )

    with pytest.raises(ValueError):
        save_identifiers_to_project(
            db_session,
            project_id=project.id,
            strategy_name="CPHI",
            identifiers={"NRGI-111111"},
        )


# ------------------------------------------------------------------
# Conflict queries
# ------------------------------------------------------------------


def test_find_project_conflicts(db_session):
    project = make_project(
        db_session,
        name="Project A",
        strategy_name="CPHI",
    )

    save_identifiers_to_project(
        db_session,
        project_id=project.id,
        strategy_name="CPHI",
        identifiers={
            "NRGI-111111",
            "NRGI-222222",
        },
    )

    conflicts = find_project_conflicts(
        db_session,
        project_id=project.id,
        identifiers={
            "NRGI-111111",
            "NRGI-999999",
        },
    )

    assert conflicts == {"NRGI-111111"}


def test_find_strategy_conflicts_across_projects(
    db_session,
):
    project_a = make_project(
        db_session,
        name="Project A",
        strategy_name="CPHI",
    )

    project_b = make_project(
        db_session,
        name="Project B",
        strategy_name="CPHI",
    )

    save_identifiers_to_project(
        db_session,
        project_id=project_a.id,
        strategy_name="CPHI",
        identifiers={"NRGI-111111"},
    )

    save_identifiers_to_project(
        db_session,
        project_id=project_b.id,
        strategy_name="CPHI",
        identifiers={"NRGI-222222"},
    )

    conflicts = find_strategy_conflicts(
        db_session,
        strategy_name="CPHI",
        identifiers={
            "NRGI-111111",
            "NRGI-222222",
            "NRGI-999999",
        },
    )

    assert conflicts == {
        "NRGI-111111",
        "NRGI-222222",
    }


def test_find_other_project_matches(db_session):
    selected_project = make_project(
        db_session,
        name="Selected Project",
        strategy_name="CPHI",
    )

    other_project = make_project(
        db_session,
        name="Other Project",
        strategy_name="CPHI",
    )

    save_identifiers_to_project(
        db_session,
        project_id=other_project.id,
        strategy_name="CPHI",
        identifiers={"NRGI-222222"},
    )

    matches = find_other_project_matches(
        db_session,
        project_id=selected_project.id,
        strategy_name="CPHI",
        identifiers={"NRGI-222222"},
    )

    assert matches == {
        "NRGI-222222": ["Other Project"],
    }


# ------------------------------------------------------------------
# Database comparison scope
# ------------------------------------------------------------------


def test_selected_project_produces_hard_and_soft_matches(
    db_session,
):
    selected_project = make_project(
        db_session,
        name="Project A",
        strategy_name="CPHI",
    )

    other_project = make_project(
        db_session,
        name="Project B",
        strategy_name="CPHI",
    )

    save_identifiers_to_project(
        db_session,
        project_id=selected_project.id,
        strategy_name="CPHI",
        identifiers={"NRGI-111111"},
    )

    save_identifiers_to_project(
        db_session,
        project_id=other_project.id,
        strategy_name="CPHI",
        identifiers={"NRGI-222222"},
    )

    comparison = compare_identifiers_to_database(
        db_session,
        strategy_name="CPHI",
        project_id=selected_project.id,
        identifiers={
            "NRGI-111111",
            "NRGI-222222",
            "NRGI-999999",
        },
    )

    assert comparison.hard_conflicts == {
        "NRGI-111111"
    }

    assert comparison.soft_warnings == {
        "NRGI-222222": ["Project B"],
    }

    assert (
        comparison.hard_conflict_scope.scope_type
        == "project"
    )

    assert (
        comparison.hard_conflict_scope.display_name
        == "Project A"
    )


def test_no_selected_project_uses_strategy_wide_hard_scope(
    db_session,
):
    project_a = make_project(
        db_session,
        name="Project A",
        strategy_name="CPHI",
    )

    project_b = make_project(
        db_session,
        name="Project B",
        strategy_name="CPHI",
    )

    save_identifiers_to_project(
        db_session,
        project_id=project_a.id,
        strategy_name="CPHI",
        identifiers={"NRGI-111111"},
    )

    save_identifiers_to_project(
        db_session,
        project_id=project_b.id,
        strategy_name="CPHI",
        identifiers={"NRGI-222222"},
    )

    comparison = compare_identifiers_to_database(
        db_session,
        strategy_name="CPHI",
        project_id=None,
        identifiers={
            "NRGI-111111",
            "NRGI-222222",
        },
    )

    assert comparison.hard_conflicts == {
        "NRGI-111111",
        "NRGI-222222",
    }

    assert comparison.soft_warnings == {}

    assert (
        comparison.hard_conflict_scope.scope_type
        == "strategy"
    )


def test_resolve_database_scope_rejects_strategy_mismatch(
    db_session,
):
    project = make_project(
        db_session,
        name="Project A",
        strategy_name="CPHI",
    )

    with pytest.raises(ValueError):
        resolve_database_scope(
            db_session,
            strategy_name="PCGL",
            project_id=project.id,
        )


# ------------------------------------------------------------------
# Generation reservation scope
# ------------------------------------------------------------------


def test_generation_reserved_ids_selected_project_only(
    db_session,
):
    project_a = make_project(
        db_session,
        name="Project A",
        strategy_name="CPHI",
    )

    project_b = make_project(
        db_session,
        name="Project B",
        strategy_name="CPHI",
    )

    save_identifiers_to_project(
        db_session,
        project_id=project_a.id,
        strategy_name="CPHI",
        identifiers={"NRGI-111111"},
    )

    save_identifiers_to_project(
        db_session,
        project_id=project_b.id,
        strategy_name="CPHI",
        identifiers={"NRGI-222222"},
    )

    reserved = get_hard_reserved_identifiers_for_generation(
        db_session,
        strategy_name="CPHI",
        project_id=project_a.id,
    )

    assert reserved == {"NRGI-111111"}


def test_generation_reserved_ids_strategy_wide_without_project(
    db_session,
):
    project_a = make_project(
        db_session,
        name="Project A",
        strategy_name="CPHI",
    )

    project_b = make_project(
        db_session,
        name="Project B",
        strategy_name="CPHI",
    )

    save_identifiers_to_project(
        db_session,
        project_id=project_a.id,
        strategy_name="CPHI",
        identifiers={"NRGI-111111"},
    )

    save_identifiers_to_project(
        db_session,
        project_id=project_b.id,
        strategy_name="CPHI",
        identifiers={"NRGI-222222"},
    )

    reserved = get_hard_reserved_identifiers_for_generation(
        db_session,
        strategy_name="CPHI",
        project_id=None,
    )

    assert reserved == {
        "NRGI-111111",
        "NRGI-222222",
    }
    