"""
Database comparison helpers for validation and generation results.

This module compares identifiers produced by the pipeline with identifiers
already stored in the database.

Database scope rules
--------------------
When a Project Tag is selected:

- Matches inside the selected project are hard conflicts.
- Matches in other projects under the same strategy are soft warnings.

When no Project Tag is selected:

- Matches anywhere under the selected strategy are hard conflicts.
- No soft-warning scope is used.

How this file connects to the project
-------------------------------------
- ``api/validate.py`` calls ``compare_pipeline_result_to_database()`` after
  format validation finishes.
- ``api/generate.py`` uses
  ``get_hard_reserved_identifiers_for_generation()`` before generation and
  runs the final comparison afterward.
- ``db/identifier_repository.py`` contains the database queries used here.
- ``db/project_repository.py`` confirms that the selected project exists and
  belongs to the requested strategy.
- ``core/pipeline_response.py`` rebuilds ``clean_records`` and the summary after
  database conflicts are added.

Adding a new strategy
---------------------
This file normally does not need to change when a strategy is added because
comparisons use the stored ``strategy_name`` rather than strategy-specific
rules.

Changes are only needed here when a new strategy returns identifiers in a
different pipeline-result field or needs different database-scope behavior.
In that case, update ``get_identifiers_from_row_result()`` and the related
comparison tests.
"""

from dataclasses import dataclass
from typing import Literal

from sqlalchemy.orm import Session

from core.pipeline_response import (
    rebuild_clean_records,
    rebuild_summary,
)
from db.identifier_repository import (
    find_other_project_matches,
    find_project_conflicts,
    find_strategy_conflicts,
    list_identifiers_by_project,
    list_identifiers_by_strategy,
)
from db.project_repository import get_project_by_id


@dataclass
class DatabaseScope:
    """
    Describe the database scope used for hard-conflict checks.

    ``scope_type`` is either ``"project"`` or ``"strategy"``.
    ``display_name`` is used in user-facing conflict messages.
    """

    scope_type: Literal["project", "strategy"]
    display_name: str
    strategy_name: str


@dataclass
class DatabaseComparison:
    """
    Store the hard conflicts and soft warnings found in the database.

    ``hard_conflicts`` contains identifiers that already exist in the active
    conflict scope.

    ``soft_warnings`` maps identifiers to the names of other projects where
    they were found.
    """

    hard_conflicts: set[str]
    hard_conflict_scope: DatabaseScope
    soft_warnings: dict[str, list[str]]


def compare_identifiers_to_database(
    session: Session,
    *,
    strategy_name: str,
    project_id: int | None,
    identifiers: set[str],
) -> DatabaseComparison:
    """
    Compare identifiers with the correct database scope.

    Parameters
    ----------
    session:
        Active SQLAlchemy session.

    strategy_name:
        Strategy used by the current validation or generation request.

    project_id:
        Optional selected Project Tag.

    identifiers:
        Identifier values that passed the pipeline checks.

    Returns
    -------
    DatabaseComparison
        Hard conflicts, soft warnings, and the scope used for hard conflicts.
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
    strategy_name: str,
    project_id: int | None,
) -> DatabaseScope:
    """
    Resolve the scope used for hard-conflict checks.

    With a selected project, hard conflicts are limited to that project.
    Without one, the full strategy becomes the hard-conflict scope.

    Raises
    ------
    ValueError
        Raised when the selected project does not exist or belongs to a
        different strategy.
    """
    if project_id is None:
        return DatabaseScope(
            scope_type="strategy",
            display_name=strategy_name,
            strategy_name=strategy_name,
        )

    project = get_project_by_id(
        session,
        project_id=project_id,
    )

    if project is None:
        raise ValueError(
            f"Project with id {project_id} was not found."
        )

    if project.strategy_name != strategy_name:
        raise ValueError(
            f"Project '{project.name}' uses strategy "
            f"'{project.strategy_name}', but the request uses "
            f"'{strategy_name}'."
        )

    return DatabaseScope(
        scope_type="project",
        display_name=project.name,
        strategy_name=project.strategy_name,
    )


def get_hard_reserved_identifiers_for_generation(
    session: Session,
    *,
    strategy_name: str,
    project_id: int | None,
) -> set[str]:
    """
    Return stored identifiers that generation must avoid.

    These values are passed into the generation pipeline before new identifiers
    are created. This allows the pipeline to regenerate a candidate before it
    reaches the final database-comparison step.
    """
    scope = resolve_database_scope(
        session,
        strategy_name=strategy_name,
        project_id=project_id,
    )

    if scope.scope_type == "project":
        assert project_id is not None

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
    row_result: dict,
) -> set[str]:
    """
    Extract identifiers that should be checked against the database.

    Normal validation and fill-missing generation use
    ``row_result["identifier"]``.

    Derived generation uses the values inside
    ``row_result["generated_identifiers"]`` because the regular identifier
    field contains the original source ID.
    """
    generated_identifiers = row_result.get(
        "generated_identifiers"
    )

    if isinstance(generated_identifiers, dict):
        return {
            identifier.strip()
            for identifier in generated_identifiers.values()
            if (
                isinstance(identifier, str)
                and identifier.strip()
            )
        }

    identifier = row_result.get("identifier")

    if isinstance(identifier, str) and identifier.strip():
        return {
            identifier.strip()
        }

    return set()


def collect_valid_identifiers_from_results(
    pipeline_result: dict,
) -> set[str]:
    """
    Collect database-checkable identifiers from currently valid rows.

    Invalid pipeline rows are skipped because they are already excluded from
    ``clean_records`` and do not need another conflict check.
    """
    identifiers: set[str] = set()

    for row_result in pipeline_result.get(
        "results",
        [],
    ):
        if row_result.get("valid") is not True:
            continue

        identifiers.update(
            get_identifiers_from_row_result(
                row_result
            )
        )

    return identifiers


def apply_database_comparison_to_result(
    pipeline_result: dict,
    *,
    comparison: DatabaseComparison,
) -> dict:
    """
    Add database conflicts and warnings to a pipeline result.

    Hard conflict:
    - The row becomes invalid.
    - ``error`` becomes ``"Database conflict"``.
    - The existing message is replaced with a conflict explanation.

    Soft warning:
    - The row remains valid.
    - The current message is kept.
    - A warning describing the other matching projects is appended.

    After all rows are updated, ``clean_records`` and the summary are rebuilt
    so they match the final result state.
    """
    hard_conflict_row_count = 0
    soft_warning_row_count = 0

    for row_result in pipeline_result.get(
        "results",
        [],
    ):
        if row_result.get("valid") is not True:
            continue

        row_identifiers = (
            get_identifiers_from_row_result(
                row_result
            )
        )

        if not row_identifiers:
            continue

        hard_matches = (
            row_identifiers
            & comparison.hard_conflicts
        )

        if hard_matches:
            row_result["valid"] = False
            row_result["error"] = "Database conflict"
            row_result["message"] = (
                build_hard_conflict_message(
                    conflicting_identifiers=hard_matches,
                    scope=comparison.hard_conflict_scope,
                )
            )

            hard_conflict_row_count += 1
            continue

        warning_matches = (
            row_identifiers
            & set(comparison.soft_warnings)
        )

        if warning_matches:
            warning_message = (
                build_soft_warning_message(
                    warning_identifiers=warning_matches,
                    soft_warnings=comparison.soft_warnings,
                )
            )

            row_result["message"] = (
                append_warning_to_message(
                    row_result.get("message", ""),
                    warning_message,
                )
            )

            soft_warning_row_count += 1

    rebuild_clean_records(pipeline_result)

    rebuild_summary(
        pipeline_result,
        database_hard_conflict_count=(
            hard_conflict_row_count
        ),
        database_soft_warning_count=(
            soft_warning_row_count
        ),
    )

    return pipeline_result


def compare_pipeline_result_to_database(
    session: Session,
    *,
    pipeline_result: dict,
    strategy_name: str,
    project_id: int | None,
) -> dict:
    """
    Run the complete post-pipeline database comparison.

    The function collects identifiers from valid rows, queries the database,
    updates matching rows, and rebuilds the final clean output and summary.
    """
    identifiers = (
        collect_valid_identifiers_from_results(
            pipeline_result
        )
    )

    comparison = compare_identifiers_to_database(
        session,
        strategy_name=strategy_name,
        project_id=project_id,
        identifiers=identifiers,
    )

    return apply_database_comparison_to_result(
        pipeline_result,
        comparison=comparison,
    )


def build_hard_conflict_message(
    *,
    conflicting_identifiers: set[str],
    scope: DatabaseScope,
) -> str:
    """
    Build a user-facing message for one or more hard conflicts.
    """
    sorted_identifiers = sorted(
        conflicting_identifiers
    )

    if scope.scope_type == "project":
        scope_message = (
            f"project '{scope.display_name}' "
            f"under the '{scope.strategy_name}' strategy"
        )
    else:
        scope_message = (
            f"the complete '{scope.strategy_name}' "
            "strategy scope because no project was selected"
        )

    if len(sorted_identifiers) == 1:
        return (
            f"Identifier '{sorted_identifiers[0]}' "
            f"already exists in {scope_message}."
        )

    return (
        "The following identifiers already exist in "
        f"{scope_message}: "
        + ", ".join(sorted_identifiers)
        + "."
    )


def build_soft_warning_message(
    *,
    warning_identifiers: set[str],
    soft_warnings: dict[str, list[str]],
) -> str:
    """
    Build a warning describing matches found in other projects.
    """
    warning_parts: list[str] = []

    for identifier in sorted(
        warning_identifiers
    ):
        project_names = sorted(
            set(
                soft_warnings.get(
                    identifier,
                    [],
                )
            )
        )

        warning_parts.append(
            f"Identifier '{identifier}' also exists "
            "in the other project(s): "
            + ", ".join(project_names)
            + "."
        )

    return " ".join(warning_parts)


def append_warning_to_message(
    message: str,
    warning: str,
) -> str:
    """
    Append a database warning without replacing the pipeline message.
    """
    if not message:
        return f"Warning: {warning}"

    return f"{message} Warning: {warning}"