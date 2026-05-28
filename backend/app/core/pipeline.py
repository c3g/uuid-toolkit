from core.parser import parse_file
from core.normalizer import normalize
from strategies.registry import get_strategy
from core.validation_result import enforce_validation_result


MAX_GENERATION_ATTEMPTS = 20


def run_validation_pipeline(
    file_bytes: bytes,
    file_type: str,
    strategy_name: str,
    config: dict,
    id_name: str | None = None,
) -> dict:
    """
    Validate identifiers in an uploaded file.

    Validation has two layers:
    1. Structural validation using the selected strategy.
    2. File-level duplicate detection.

    If an identifier is duplicated, all rows containing that identifier
    are marked invalid.
    """

    parsed = parse_file(file_bytes, file_type)
    normalized = normalize(parsed, id_name=id_name)

    strategy = get_strategy(strategy_name, config)

    results = []
    identifier_to_rows: dict[str, list[int]] = {}

    # Pass 1: structural validation
    for record in normalized:
        raw_result = strategy.validate(
            record["identifier"],
            config,
        )

        result = enforce_validation_result(raw_result)

        row_result = {
            "row_index": record["row_index"],
            "id_field": record["id_field"],
            "identifier": record["identifier"],
            "metadata": record["metadata"],
            **result,
        }

        results.append(row_result)

        # Only structurally valid IDs are checked for duplicates.
        if result["valid"] is True:
            identifier = record["identifier"]
            identifier_to_rows.setdefault(identifier, []).append(record["row_index"])

    # Pass 2: duplicate detection
    duplicate_row_indexes = find_duplicate_row_indexes(identifier_to_rows)

    for row_result in results:
        row_index = row_result["row_index"]

        if row_index in duplicate_row_indexes:
            identifier = row_result["identifier"]
            duplicate_rows = identifier_to_rows[identifier]

            row_result["valid"] = False
            row_result["error"] = "Duplicate identifier"
            row_result["message"] = (
                "Identifier appears more than once in the uploaded file. "
                f"Duplicate rows: {duplicate_rows}."
            )

    clean_records = []

    for record, row_result in zip(normalized, results):
        if row_result["valid"] is True:
            clean_records.append(record["original_record"].copy())

    valid_count = sum(1 for row in results if row["valid"] is True)
    invalid_count = len(results) - valid_count
    duplicate_count = len(duplicate_row_indexes)

    return {
        "mode": "validation",
        "summary": {
            "total_rows": len(results),
            "valid_count": valid_count,
            "invalid_count": invalid_count,
            "duplicate_count": duplicate_count,
            "clean_count": len(clean_records),
        },
        "results": results,
        "clean_records": clean_records,
    }


def run_generation_pipeline(
    file_bytes: bytes,
    file_type: str,
    strategy_name: str,
    config: dict | None = None,
    id_name: str | None = None,
    output_id_field: str = "identifier",
) -> dict:
    """
    Generate missing identifiers in an uploaded file.

    Rules:
    - Existing IDs are not overwritten.
    - Existing-existing duplicate IDs are marked as conflicts.
    - Missing IDs are generated.
    - If a generated ID conflicts with an existing ID, regenerate the generated ID.
    - If generated IDs conflict with each other, keep the first one and regenerate later ones.
    """

    config = config or {}

    parsed = parse_file(file_bytes, file_type)
    normalized_records = normalize(parsed, id_name=id_name)

    strategy = get_strategy(strategy_name, config)

    existing_identifier_to_rows: dict[str, list[int]] = {}
    existing_validation_results: dict[int, dict] = {}
    missing_row_indexes: list[int] = []

    # Pass 1:
    # Separate existing IDs from missing IDs.
    # Validate existing IDs structurally.
    for record in normalized_records:
        row_index = record["row_index"]
        identifier = record["identifier"]

        if identifier is None:
            missing_row_indexes.append(row_index)
            continue

        raw_result = strategy.validate(identifier, config)
        result = enforce_validation_result(raw_result)

        existing_validation_results[row_index] = result

        if result["valid"] is True:
            existing_identifier_to_rows.setdefault(identifier, []).append(row_index)

    # Existing-existing duplicates.
    duplicate_existing_row_indexes = find_duplicate_row_indexes(
        existing_identifier_to_rows
    )

    # Existing IDs are reserved.
    # Generated IDs must not collide with any valid existing ID,
    # even if the existing ID itself is duplicated.
    existing_identifiers = set(existing_identifier_to_rows.keys())

    # Pass 2:
    # Generate IDs for all missing rows first.
    generated_by_row: dict[int, str] = {}

    for row_index in missing_row_indexes:
        generated_by_row[row_index] = strategy.generate(config)

    # Pass 3:
    # Resolve generated-existing and generated-generated conflicts.
    unresolved_generated_conflict_rows = resolve_generated_conflicts(
        generated_by_row=generated_by_row,
        existing_identifiers=existing_identifiers,
        strategy=strategy,
        config=config,
        max_attempts=MAX_GENERATION_ATTEMPTS,
    )

    updated_records = []
    clean_records = []
    results = []

    generated_count = 0
    skipped_count = 0
    duplicate_count = 0
    error_count = 0
    generation_conflict_count = 0

    # Pass 4:
    # Build final row-level output.
    for record in normalized_records:
        row_index = record["row_index"]
        existing_identifier = record["identifier"]

        updated_row = record["original_record"].copy()
        target_id_field = record["id_field"] or output_id_field

        # Case 1: row already had an identifier
        if existing_identifier is not None:
            validation_result = existing_validation_results[row_index]

            # Existing ID is structurally invalid.
            if validation_result["valid"] is False:
                error_count += 1

                results.append({
                    "row_index": row_index,
                    "id_field": target_id_field,
                    "action": "existing_id_invalid",
                    "identifier": existing_identifier,
                    "valid": False,
                    "error": validation_result["error"],
                    "message": validation_result["message"],
                })

                updated_records.append(updated_row)
                continue

            # Existing ID is structurally valid but duplicated in the file.
            if row_index in duplicate_existing_row_indexes:
                duplicate_count += 1
                duplicate_rows = existing_identifier_to_rows[existing_identifier]

                results.append({
                    "row_index": row_index,
                    "id_field": target_id_field,
                    "action": "duplicate_existing_id",
                    "identifier": existing_identifier,
                    "valid": False,
                    "error": "Duplicate identifier",
                    "message": (
                        "Existing identifier appears more than once in the uploaded file. "
                        f"Duplicate rows: {duplicate_rows}."
                    ),
                    "metadata": record["metadata"],
                })

                updated_records.append(updated_row)
                continue

            # Existing ID is valid and not duplicated.
            skipped_count += 1

            results.append({
                "row_index": row_index,
                "id_field": target_id_field,
                "action": "skipped_existing_id",
                "identifier": existing_identifier,
                "valid": True,
                "error": None,
                "message": "Existing identifier was left unchanged.",
                "metadata": record["metadata"],
            })

            updated_records.append(updated_row)
            clean_records.append(updated_row.copy())
            continue

        # Case 2: row was missing an identifier
        generated_identifier = generated_by_row.get(row_index)

        if row_index in unresolved_generated_conflict_rows:
            error_count += 1
            generation_conflict_count += 1

            results.append({
                "row_index": row_index,
                "id_field": target_id_field,
                "action": "generation_failed",
                "identifier": generated_identifier,
                "valid": False,
                "error": "Generation conflict",
                "message": (
                    "Could not generate a unique identifier after "
                    f"{MAX_GENERATION_ATTEMPTS} conflict-resolution attempts."
                ),
                "metadata": record["metadata"],
            })

            updated_records.append(updated_row)
            continue

        updated_row[target_id_field] = generated_identifier

        generated_count += 1

        results.append({
            "row_index": row_index,
            "id_field": target_id_field,
            "action": "generated",
            "identifier": generated_identifier,
            "valid": True,
            "error": None,
            "message": "Missing identifier was generated.",
            "metadata": record["metadata"],
        })

        updated_records.append(updated_row)
        clean_records.append(updated_row.copy())

    return {
        "mode": "generation",
        "summary": {
            "total_rows": len(updated_records),
            "generated_count": generated_count,
            "skipped_count": skipped_count,
            "duplicate_count": duplicate_count,
            "generation_conflict_count": generation_conflict_count,
            "error_count": error_count,
            "clean_count": len(clean_records),
        },
        "results": results,
        "updated_records": updated_records,
        "clean_records": clean_records,
    }


def find_duplicate_row_indexes(
    identifier_to_rows: dict[str, list[int]]
) -> set[int]:
    """
    Return all row indexes involved in duplicate conflicts.

    Example:
        {
            "ID1": [0, 3],
            "ID2": [1],
            "ID3": [2, 5],
        }

    Returns:
        {0, 3, 2, 5}
    """

    duplicate_row_indexes = set()

    for rows in identifier_to_rows.values():
        if len(rows) > 1:
            duplicate_row_indexes.update(rows)

    return duplicate_row_indexes


def resolve_generated_conflicts(
    generated_by_row: dict[int, str],
    existing_identifiers: set[str],
    strategy,
    config: dict,
    max_attempts: int,
) -> set[int]:
    """
    Resolve conflicts involving generated IDs.

    Conflict types:
    1. generated-existing:
        Generated ID already exists in the uploaded file.
        Regenerate the generated row.

    2. generated-generated:
        Two generated rows received the same ID.
        Keep the first generated row and regenerate later duplicate rows.

    Returns:
        set of row indexes that still have unresolved conflicts after max attempts.
    """

    unresolved_conflict_rows: set[int] = set()

    for _ in range(max_attempts):
        conflict_rows = find_generated_conflict_rows(
            generated_by_row=generated_by_row,
            existing_identifiers=existing_identifiers,
        )

        if not conflict_rows:
            return set()

        unresolved_conflict_rows = conflict_rows

        for row_index in conflict_rows:
            generated_by_row[row_index] = strategy.generate(config)

    # Final check after all attempts.
    return find_generated_conflict_rows(
        generated_by_row=generated_by_row,
        existing_identifiers=existing_identifiers,
    )


def find_generated_conflict_rows(
    generated_by_row: dict[int, str],
    existing_identifiers: set[str],
) -> set[int]:
    """
    Find generated rows that currently have conflicts.

    Rules:
    - If generated ID conflicts with an existing ID, regenerate that generated row.
    - If generated ID conflicts with another generated ID, keep the first row and
      regenerate later rows.
    """

    conflict_rows: set[int] = set()

    # generated-existing conflicts
    for row_index, generated_identifier in generated_by_row.items():
        if generated_identifier in existing_identifiers:
            conflict_rows.add(row_index)

    # generated-generated conflicts
    generated_identifier_to_rows: dict[str, list[int]] = {}

    for row_index, generated_identifier in generated_by_row.items():
        generated_identifier_to_rows.setdefault(generated_identifier, []).append(row_index)

    for rows in generated_identifier_to_rows.values():
        if len(rows) > 1:
            sorted_rows = sorted(rows)

            # Option B:
            # Keep the first generated row, regenerate later duplicate rows.
            later_duplicate_rows = sorted_rows[1:]

            for row_index in later_duplicate_rows:
                conflict_rows.add(row_index)

    return conflict_rows