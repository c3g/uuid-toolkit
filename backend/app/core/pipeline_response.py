FILL_MISSING_EXISTING_ACTIONS = {
    "existing_id_invalid",
    "duplicate_existing_id",
    "skipped_existing_id",
}


def rebuild_clean_records(
    pipeline_result: dict,
) -> None:
    """
    Rebuild clean_records using the final validity of each result row.

    The pipeline must provide:
    - results
    - updated_records

    Both lists must contain one entry per uploaded row and must use the
    same row order.
    """
    results = pipeline_result.get("results")
    updated_records = pipeline_result.get("updated_records")

    if not isinstance(results, list):
        raise ValueError(
            "Pipeline result must include a 'results' list."
        )

    if not isinstance(updated_records, list):
        raise ValueError(
            "Pipeline result must include an 'updated_records' list."
        )

    if len(results) != len(updated_records):
        raise ValueError(
            "Pipeline result 'results' and 'updated_records' must "
            "contain the same number of rows."
        )

    clean_records: list[dict] = []

    for updated_record, row_result in zip(
        updated_records,
        results,
    ):
        if row_result.get("valid") is True:
            clean_records.append(updated_record.copy())

    pipeline_result["clean_records"] = clean_records


def rebuild_summary(
    pipeline_result: dict,
    *,
    database_hard_conflict_count: int,
    database_soft_warning_count: int,
) -> None:
    """
    Rebuild final summary values after database comparison.

    Generic final-state counts are recalculated:
    - total_rows
    - valid_count
    - invalid_count
    - clean_count

    Existing mode-specific fields such as generated_count,
    duplicate_count, and generation_conflict_count are preserved.
    """
    results = pipeline_result.get("results")
    clean_records = pipeline_result.get("clean_records")

    if not isinstance(results, list):
        raise ValueError(
            "Pipeline result must include a 'results' list."
        )

    if not isinstance(clean_records, list):
        raise ValueError(
            "Pipeline result must include a 'clean_records' list."
        )

    valid_count = sum(
        1
        for row_result in results
        if row_result.get("valid") is True
    )

    invalid_count = sum(
        1
        for row_result in results
        if row_result.get("valid") is False
    )

    summary = pipeline_result.setdefault("summary", {})

    summary["total_rows"] = len(results)
    summary["valid_count"] = valid_count
    summary["invalid_count"] = invalid_count
    summary["clean_count"] = len(clean_records)

    # These count affected rows, not distinct identifier values.
    summary["database_hard_conflict_count"] = (
        database_hard_conflict_count
    )
    summary["database_soft_warning_count"] = (
        database_soft_warning_count
    )

    if pipeline_result.get("mode") == "generation":
        rebuild_generation_summary(
            pipeline_result,
            valid_count=valid_count,
            invalid_count=invalid_count,
        )


def rebuild_generation_summary(
    pipeline_result: dict,
    *,
    valid_count: int,
    invalid_count: int,
) -> None:
    """
    Update generation summary fields that describe the final row state.

    Action counts such as generated_count and duplicate_count are kept
    unchanged because they describe what the generation pipeline did.
    """
    summary = pipeline_result["summary"]
    results = pipeline_result["results"]

    # Final number of invalid generation rows.
    summary["error_count"] = invalid_count

    # These fields only exist for fill-missing generation.
    if (
        "existing_valid_count" in summary
        or "existing_invalid_count" in summary
    ):
        existing_results = [
            row_result
            for row_result in results
            if row_result.get("action")
            in FILL_MISSING_EXISTING_ACTIONS
        ]

        summary["existing_valid_count"] = sum(
            1
            for row_result in existing_results
            if row_result.get("valid") is True
        )

        summary["existing_invalid_count"] = sum(
            1
            for row_result in existing_results
            if row_result.get("valid") is False
        )