from sqlalchemy import Session
from dataclasses import dataclass
from typing import Literal

from db.identifier_repository import (
    list_identifiers,
    list_identifiers_by_project,
    list_identifiers_by_strategy,
    find_project_conflicts,
    find_strategy_conflicts,
    find_other_project_matches,
)
from db.project_repository import get_project_by_id

@dataclass
class DatabaseScope:
    scope_type: Literal["project","strategy"]
    display_name:str
    strategy_name:str

@dataclass
class DatabaseComparison:
    hard_conflicts:set[str]
    hard_conflict_scope: DatabaseScope
    soft_warnings: dict[str,list[str]]
    

def compare_identifiers_to_database(
    session: Session,
    *,
    strategy_name: str,
    project_id: int | None,
    identifiers: set[str],
) -> DatabaseComparison:
    """
    Compare identifiers against the appropriate database scope.

    With a selected project:
        hard conflicts = selected project
        soft warnings = other projects using the same strategy

    Without a selected project:
        hard conflicts = all projects using the same strategy
        soft warnings = none
    """
    scope = resolve_database_scope(
        session,
        strategy_name=strategy_name,
        project_id=project_id,
    )

    if not identifiers:
        return DatabaseComparison(
            hard_conflicts=set(),
            soft_warnings={},
            hard_conflict_scope=scope,
        )

    if project_id is None:
        hard_conflicts = find_strategy_conflicts(
            session,
            strategy_name=strategy_name,
            identifiers=identifiers,
        )

        return DatabaseComparison(
            hard_conflicts=hard_conflicts,
            soft_warnings={},
            hard_conflict_scope=scope,
        )

    hard_conflicts = find_project_conflicts(
        session,
        project_id=project_id,
        identifiers=identifiers,
    )

    soft_warnings = find_other_project_matches(
        session,
        project_id=project_id,
        strategy_name=strategy_name,
        identifiers=identifiers,
    )

    return DatabaseComparison(
        hard_conflicts=hard_conflicts,
        soft_warnings=soft_warnings,
        hard_conflict_scope=scope,
    )

def resolve_database_scope(
    session: Session,
    *,
    strategy_name:str,
    project_id: int | None,
)-> DatabaseScope:
    """
    Resolve the database scope used for hard conflicts.

    If a project is selected:
        hard conflicts are checked inside that project.

    If no project is selected:
        hard conflicts are checked across the entire strategy.
    """

    if project_id is None:
        return DatabaseScope(
            scope_type= "strategy",
            display_name=strategy_name,
            strategy_name=strategy_name,
        )
    project = get_project_by_id(
        session,
        project_id=project_id,
    )

    if project is None:
        raise ValueError(
            f"Project with id {project_id} was not found"
        )
    
    if project.strategy_name != strategy_name:
        raise ValueError(
            f"Project {project.name} uses strategy"
            f"{project.strategy_name} but the request uses {strategy_name}"
        )
    return DatabaseScope(
        scope_type = "project",
        display_name=project.name,
        strategy_name=project.strategy_name,
    )
    

def get_hard_reserved_identifiers_for_generation(
        session: Session,
        *,
        strategy_name:str,
        project_id:int |None,
) -> set[str]:
    """
    Get database identifiers that generated IDs must not duplicate.

    If project_id is provided:
        only selected-project IDs are hard reserved.

    If project_id is None:
        all same-strategy IDs are hard reserved.
    """
    if project_id is not None:
        records = list_identifiers_by_project(
            session,
            project_id=project_id,
        )
    else:
        records = list_identifiers_by_strategy(
            session,
            strategy_name=strategy_name,
        )

    return {
        record.identifier_value
        for record in records
    }

def get_identifiers_from_row_result(
    row_result:dict,
)-> set[str]:
    """
    Extract database-checkable identifiers from one pipeline result row.

    Validation:
        Uses row_result["identifier"].

    Fill-missing generation:
        Uses row_result["identifier"].

    Derived generation:
        Uses row_result["generated_identifiers"].values().

    Important:
        For derived generation, row_result["identifier"] is the source/base ID,
        so we check generated_identifiers instead when that field exists.
    """

    generated_identifiers = row_result.get("generated_identifiers")

    if isinstance(generated_identifiers,dict):
        return {
            identifier.strip()
            for identifier in generated_identifiers.values()
            if isinstance(identifier,str) and identifier.strip()
        }
    identifier = row_result.get("identifier")

    if isinstance(identifier,str) and identifier.strip():
        return {identifier.strip()}
    
    return set()

def collect_valid_identifiers_from_results(
    pipeline_result:dict,
)-> set[str]:
    """
    Collect identifiers from rows that are currently valid.

    This is used after the pipeline is finished, before applying database hard conflicts and soft warnings.
    """

    identifiers: set[str]=set()

    for row_result in pipeline_result.get("results",[]):
        if row_result.get("valid") is not True:
            continue
        identifiers.update(
            get_identifiers_from_row_result(row_result)
        )
    
    return identifiers

def apply_database_comparison_to_result(
        pipeline_result:dict,
        *,
        comparison: DatabaseComparison,
)-> dict:
    """
    We apply database hard conflicts and soft warnings to a finished pipeline result.

    Hard conflicts are defined as the following:
        - Overlapping identifiers within the same scope defined by user
        Result in:
            - Row becomes invalid
            - error becomes "Database conflict"
    
    Soft conflicts are defined as the following:
        -Overlapping identifiers outside of the user determined scopes but none within the scope.
        Result in:
            - Row stays valid
            - error stays none
            - warning is appended to the message
    """

    for row_result in pipeline_result.get("result",[]):
        if row_result.get("valid") is not True:
            continue

        row_identifiers = get_identifiers_from_row_result(row_result)

        if not row_identifiers:
            continue

        hard_matches = row_identifiers & comparison.hard_conflicts

        if hard_matches:
            row_result["valid"] = False
            row_result["error"] = "Database Conflict"
            row_result["message"] = build_hard_conflict_message(
                conflicting_identifiers = hard_matches,
            )
            continue

        warning_matches = row_identifiers & set(comparison.soft_warnings.keys())

        if warning_matches:
            warning_message = build_soft_warning_message(
                warning_identifiers = warning_matches,
                soft_warnings = comparison.soft_warnings,
            )
            row_result["message"] = append_warning_to_message(
                row_result.get("message",""),
                warning_message,
            )
    rebuild_clean_records(pipeline_result)
    rebuild_summary(pipeline_result)

    return pipeline_result

#Helper functions:


def build_hard_conflict_message(
    *,
    conflicting_identifiers: set[str],
    scope: DatabaseScope,
) -> str:
    """
    Build a hard-conflict message that explains where the conflict occurred.
    """
    sorted_identifiers = sorted(conflicting_identifiers)

    if scope.scope_type == "project":
        scope_message = (
            f"project '{scope.display_ngame}' "
            f"under the '{scope.strategy_name}' strategy"
        )
    else:
        scope_message = (
            f"the complete '{scope.strategy_name}' strategy scope "
            "because no project was selected"
        )

    if len(sorted_identifiers) == 1:
        return (
            f"Identifier '{sorted_identifiers[0]}' already exists in "
            f"{scope_message}."
        )

    return (
        "The following identifiers already exist in "
        f"{scope_message}: "
        + ", ".join(sorted_identifiers)
        + "."
    )