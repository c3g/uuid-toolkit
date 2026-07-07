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
    sheet_name: str | None = None,
) -> dict:
    """
    Validate identifiers in an uploaded file.

    Validation has two layers:
    1. Structural validation using the selected strategy.
    2. File-level duplicate detection.

    If an identifier is duplicated, all rows containing that identifier
    are marked invalid.
    """

    parsed = parse_file(
        file_bytes,
        file_type,
        id_name=id_name,
        sheet_name=sheet_name,
    )
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

        result["message"] = add_warnings_to_message(result["message"],record.get("warnings",[]),)

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
            duplicate_msg = (
                "Identifier appears more than once in the uploaded file. "
                f"Duplicate rows: {duplicate_rows}."
            )
            row_result["message"] = add_warnings_to_message(
                duplicate_msg,
                normalized[row_index].get("warnings",[]),
            )

    clean_records = []

    for record, row_result in zip(normalized, results):
        if row_result["valid"] is True:
            clean_record=record["original_record"].copy()

            if row_result["id_field"] is not None:
                clean_record[row_result["id_field"]]=row_result["identifier"]
            
            clean_records.append(clean_record)

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
        config: dict |None = None,
        id_name: str | None = None,
        output_id_field: str = "identifier",
        sheet_name: str |None = None,
) -> dict:
    """
    Run the identifier generation pipeline for an uploaded file.

    This function is the main entry point for generation requests. It parses the
    uploaded file, normalizes the parsed records, loads the selected identifier
    strategy, and then chooses the correct generation workflow based on the
    strategy's generation mode.

    The actual generation logic is delegated to one of the reusable generation
    workflows:

    - ``fill_missing``:
        Used when missing identifiers should be generated while valid existing
        identifiers are preserved.

    - ``derive_from_existing``:
        Used when one or more new identifiers should be derived from an existing
        source/base identifier. This is useful for strategies that generate
        several output columns, such as PCGL derived variant identifiers.

    The generation mode is provided by ``strategy.get_strategy_info(config)``.
    If the strategy does not define a generation mode, the pipeline defaults to
    ``fill_missing``.

    Parameters
    ----------
    file_bytes:
        Raw bytes from the uploaded file.

    file_type:
        File type of the uploaded file. This determines how the parser reads the
        file. Supported values depend on ``parse_file``, such as ``"csv"``,
        ``"json"``, or ``"xlsx"``.

    strategy_name:
        Name of the identifier strategy to use. This value is passed to the
        strategy registry so the correct validation and generation behavior can
        be loaded.

    config:
        Optional strategy-specific configuration values. These values are passed
        into the selected strategy and may include fields such as project code,
        entity type, variant, variants, UUID version, or custom format settings.
        If ``None`` is provided, an empty dictionary is used.

    id_name:
        Optional name of the input identifier column. If provided, the parser and
        normalizer use this column to find existing identifiers in the uploaded
        records.

    output_id_field:
        Name of the column where generated identifiers should be written when an
        input row does not already have an identifier column. Defaults to
        ``"identifier"``.

    sheet_name:
        Optional worksheet name for XLSX uploads. If no sheet name is provided,
        the parser uses the active worksheet.

    Returns
    -------
    dict
        A dictionary containing the generation response. The exact summary fields
        depend on the generation mode, but the response generally includes:

        ``mode``:
            The pipeline mode. For this function, the value is ``"generation"``.

        ``generation_mode``:
            The generation workflow used, such as ``"derive_from_existing"``.
            Some generation responses may omit this field when using the default
            fill-missing workflow.

        ``summary``:
            Counts describing what happened during generation, such as total
            rows, generated rows, skipped rows, invalid rows, duplicate rows, or
            clean rows.

        ``results``:
            Row-level results describing each row's action, identifier, validity,
            error message, user-facing message, metadata, and any generated
            identifiers.

        ``updated_records``:
            All uploaded records after generation has been applied. This is used
            for downloading the full output, including both successful and
            unsuccessful rows.

        ``clean_records``:
            Only the rows that are valid and safe to use after generation. This
            is used for downloading the clean output.

    Raises
    ------
    ValueError
        If the selected strategy returns an unsupported generation mode.

    """
    config = config or {}

    parsed = parse_file(
        file_bytes, 
        file_type, 
        id_name = id_name, 
        sheet_name=sheet_name
    )
    normalized_records = normalize(parsed, id_name = id_name)
    
    strategy = get_strategy(strategy_name, config)
    strategy_info = strategy.get_strategy_info(config)

    generation_mode = strategy_info.get("generation_mode", "fill_missing")

    if generation_mode == "fill_missing":
        return run_fill_missing_generation(
            normalized_records = normalized_records,
            strategy=strategy,
            config= config,
            output_id_field = output_id_field,
        )
    if generation_mode == "derive_from_existing":
        return run_derive_from_existing_generation(
            normalized_records = normalized_records,
            strategy=strategy,
            config= config,
            output_id_field = output_id_field,
        )
    raise ValueError(f"Unsupported generation mode '{generation_mode}'.")

def run_fill_missing_generation(
    normalized_records:list[dict],
        strategy,
        config:dict,
        output_id_field: str,
)-> dict:
    """
    Generate identifiers for rows that are missing an identifier.

    This function is used for the normal generation workflow where some rows may
    already have identifiers and some rows may be missing them.

    The main idea is:
    - If a row already has an identifier, validate it and leave it unchanged.
    - If a row is missing an identifier, generate a new one.
    - If an existing identifier is invalid or duplicated, report it as an error.
    - If a generated identifier conflicts with another ID, try to regenerate it.

    This function does not overwrite existing identifiers just because they are
    invalid. Invalid existing IDs are kept in the updated records but are not added
    to the clean records.

    Parameters
    ----------
    normalized_records:
        A list of records that already went through the normalizer.

        Each record should contain information such as the row index, the identifier,
        the ID column name, the original row, metadata, and any warnings that came
        from normalization.

    strategy:
        The strategy object used to validate existing identifiers and generate new
        identifiers.

        For example, this could be the UUID, CPHI, PCGL, or custom strategy.

    config:
        A dict containing the values needed by the strategy.

        For example, this may include the project code, entity type, UUID version,
        variant, or custom format options depending on the selected strategy.

    output_id_field:
        The column name that should be used when a row does not already have an ID
        column.

        If the uploaded file already has an ID column, that existing column is used.
        If not, this value is used as the new column name.

    Returns
    -------
    dict:
        A dict containing the generation results.

        The returned dict has the following format:

        {
            "mode": "generation",
            "summary": {
                "total_rows": ...,
                "existing_count": ...,
                "missing_count": ...,
                "generated_count": ...,
                "existing_valid_count": ...,
                "existing_invalid_count": ...,
                "skipped_count": ...,
                "duplicate_count": ...,
                "generation_conflict_count": ...,
                "error_count": ...,
                "clean_count": ...
            },
            "results": ...,
            "updated_records": ...,
            "clean_records": ...
        }

        results:
            Row-level information showing what happened to each row.

        updated_records:
            All rows after generation has been applied. This includes valid rows,
            invalid rows, generated rows, and skipped rows.

        clean_records:
            Only the rows that are valid and safe to use.
    """
    
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

        result["message"] = add_warnings_to_message(
            result["message"],
            record.get("warnings",[]),
        )

        existing_validation_results[row_index] = result

        if result["valid"] is True:
            existing_identifier_to_rows.setdefault(identifier, []).append(row_index)

    # Existing-existing duplicates.
    duplicate_existing_row_indexes = find_duplicate_row_indexes(
        existing_identifier_to_rows
    )
    existing_count = len (normalized_records) - len(missing_row_indexes)
    missing_count = len(missing_row_indexes)
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

    existing_valid_count = 0
    existing_invalid_count = 0

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
                existing_invalid_count += 1

                updated_row[target_id_field] = existing_identifier

                results.append({
                    "row_index": row_index,
                    "id_field": target_id_field,
                    "action": "existing_id_invalid",
                    "identifier": existing_identifier,
                    "valid": False,
                    "error": validation_result["error"],
                    "message": validation_result["message"],
                    "metadata": record["metadata"]
                })

                updated_records.append(updated_row)
                continue

            # Existing ID is structurally valid but duplicated in the file.
            if row_index in duplicate_existing_row_indexes:
                duplicate_count += 1
                existing_invalid_count += 1
                duplicate_rows = existing_identifier_to_rows[existing_identifier]

                updated_row[target_id_field] = existing_identifier

                duplicate_message = (
                    "Existing identifier appears more than once in the uploaded file. "
                    f"Duplicate rows: {duplicate_rows}."
                )
                duplicate_message = add_warnings_to_message(
                    duplicate_message,
                    record.get("warnings",[]),
                )

                results.append({
                    "row_index": row_index,
                    "id_field": target_id_field,
                    "action": "duplicate_existing_id",
                    "identifier": existing_identifier,
                    "valid": False,
                    "error": "Duplicate identifier",
                    "message": duplicate_message,
                    "metadata": record["metadata"],
                })

                updated_records.append(updated_row)
                continue

            # Existing ID is valid and not duplicated.
            skipped_count += 1
            existing_valid_count += 1

            #Passing in the cleaned value instead of the old value
            updated_row[target_id_field] = existing_identifier
            message = add_warnings_to_message(
                "Existing identifier was left unchanged",
                record.get("warnings",[])
            )

            results.append({
                "row_index": row_index,
                "id_field": target_id_field,
                "action": "skipped_existing_id",
                "identifier": existing_identifier,
                "valid": True,
                "error": None,
                "message": message,
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

            "existing_count": existing_count,
            "missing_count": missing_count,
            "generated_count": generated_count,

            "existing_valid_count": existing_valid_count,
            "existing_invalid_count": existing_invalid_count,
            
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
    
def run_derive_from_existing_generation(
    normalized_records: list[dict],
    strategy,
    config: dict,
    output_id_field: str,
) -> dict:
    """
    Generate derived identifiers from existing source identifiers.

    This function is used when the uploaded file already has a base/source ID and
    the strategy needs to generate one or more new identifiers from it.

    This is different from fill-missing generation because the source identifier is
    required. If the source identifier is missing, the row is invalid and no derived
    identifier is generated for that row.

    The main idea is:
    - Check that each row has a source identifier.
    - Use the strategy to validate the source identifier.
    - Generate one or more derived identifiers from the valid source identifier.
    - Check for duplicate source identifiers.
    - Check that generated derived identifiers do not conflict with existing source
    IDs or with each other.
    - Add the generated identifiers as new columns while keeping the original source
    ID column.

    This is useful for generation modes where one base ID can create several
    variant IDs, such as PCGL derived identifiers.

    Parameters
    ----------
    normalized_records:
        A list of records that already went through the normalizer.

        Each record should contain information such as the row index, the identifier,
        the ID column name, the original row, metadata, and any warnings that came
        from normalization.

    strategy:
        The strategy object used to generate derived identifiers.

        The strategy must have a generate_derived_identifiers method. That method
        should also validate the source identifier before generating the derived IDs.

    config:
        A dict containing the values needed by the strategy.

        For example, this may include the project code, entity type, selected
        variants, or other options needed for derived generation.

    output_id_field:
        The base column name used when creating the generated output columns.

        For example, if output_id_field is "identifier" and the strategy generates
        EXP and LIB identifiers, the output columns may become:

        {
            "identifier_EXP": "...",
            "identifier_LIB": "..."
        }

    Returns
    -------
    dict:
        A dict containing the derived generation results.

        The returned dict has the following format:

        {
            "mode": "generation",
            "generation_mode": "derive_from_existing",
            "summary": {
                "total_rows": ...,
                "generated_row_count": ...,
                "generated_identifier_count": ...,
                "missing_source_count": ...,
                "duplicate_source_count": ...,
                "source_invalid_count": ...,
                "generation_conflict_count": ...,
                "error_count": ...,
                "clean_count": ...
            },
            "results": ...,
            "updated_records": ...,
            "clean_records": ...
        }

        results:
            Row-level information showing what happened to each row.

        updated_records:
            All rows after derived generation has been applied. Successful rows will
            have the generated columns added. Invalid rows are still included but do
            not get generated columns.

        clean_records:
            Only the rows where derived generation was successful.
    """

    immediate_invalid_results: dict[int, dict] = {}
    generated_by_row: dict[int, dict[str, str]] = {}
    source_identifier_by_row: dict[int, str] = {}
    target_id_field_by_row: dict[int, str] = {}

    source_identifier_to_rows: dict[str, list[int]] = {}

    missing_source_count = 0
    duplicate_source_count = 0
    source_invalid_count = 0

    # Pass 1:
    # Validate source IDs and generate candidate derived IDs.
    for record in normalized_records:
        row_index = record["row_index"]
        source_identifier = record["identifier"]
        target_id_field = record["id_field"] or output_id_field

        target_id_field_by_row[row_index] = target_id_field

        #Check to see if the base identifier exists
        if source_identifier is None:
            missing_source_count += 1

            immediate_invalid_results[row_index] = {
                "row_index": row_index,
                "id_field": target_id_field,
                "action": "source_id_missing",
                "identifier": None,
                "valid": False,
                "error": "Missing source identifier",
                "message": "A source identifier is required for derived generation.",
                "metadata": record["metadata"],
            }
            continue

        try:
            #generate_derived_identifiers helps validate the base PCGL ID to make sure it follows the format
            raw_generated_outputs = strategy.generate_derived_identifiers(
                source_identifier,
                config,
            )
        except ValueError as error:
            source_invalid_count += 1

            message = add_warnings_to_message(
                str(error),
                record.get("warnings", []),
            )

            immediate_invalid_results[row_index] = {
                "row_index": row_index,
                "id_field": target_id_field,
                "action": "source_id_invalid",
                "identifier": source_identifier,
                "valid": False,
                "error": "Invalid source identifier",
                "message": message,
                "metadata": record["metadata"],
            }
            continue

        generated_columns = build_derived_output_columns(
            raw_generated_outputs,
            target_id_field,
        )

        generated_by_row[row_index] = generated_columns
        source_identifier_by_row[row_index] = source_identifier
        source_identifier_to_rows.setdefault(source_identifier, []).append(row_index)

    # Pass 2:
    # Check duplicates only among source IDs that passed validation.
    duplicate_source_row_indexes = find_duplicate_row_indexes(
        source_identifier_to_rows
    )

    for row_index in duplicate_source_row_indexes:
        duplicate_source_count += 1

        source_identifier = source_identifier_by_row[row_index]
        target_id_field = target_id_field_by_row[row_index]
        duplicate_rows = source_identifier_to_rows[source_identifier]

        duplicate_message = (
            "Source identifier appears more than once in the uploaded file. "
            f"Duplicate rows: {duplicate_rows}."
        )

        immediate_invalid_results[row_index] = {
            "row_index": row_index,
            "id_field": target_id_field,
            "action": "duplicate_source_id",
            "identifier": source_identifier,
            "valid": False,
            "error": "Duplicate source identifier",
            "message": duplicate_message,
            "metadata": {},
        }

        generated_by_row.pop(row_index, None)
        source_identifier_by_row.pop(row_index, None)

    existing_identifiers = set(source_identifier_to_rows.keys())

    # Pass 3:
    # Resolve generated-generated and generated-existing conflicts.
    unresolved_generated_conflict_rows = resolve_derived_generated_conflicts(
        generated_by_row=generated_by_row,
        existing_identifiers=existing_identifiers,
        source_identifier_by_row=source_identifier_by_row,
        strategy=strategy,
        config=config,
        target_id_field_by_row=target_id_field_by_row,
        max_attempts=MAX_GENERATION_ATTEMPTS,
    )

    results = []
    updated_records = []
    clean_records = []

    generated_row_count = 0
    generated_identifier_count = 0
    generation_conflict_count = 0

    # Pass 4:
    # Build final row-level output in original row order.
    for record in normalized_records:
        row_index = record["row_index"]
        source_identifier = record["identifier"]

        updated_row = record["original_record"].copy()
        target_id_field = target_id_field_by_row.get(
            row_index,
            record["id_field"] or output_id_field,
        )

        if row_index in immediate_invalid_results:
            invalid_result = immediate_invalid_results[row_index]
            invalid_result["metadata"] = record["metadata"]

            results.append(invalid_result)
            updated_records.append(updated_row)
            continue

        if row_index in unresolved_generated_conflict_rows:
            generation_conflict_count += 1

            results.append({
                "row_index": row_index,
                "id_field": target_id_field,
                "action": "derived_generation_conflict",
                "identifier": source_identifier,
                "valid": False,
                "error": "Generation conflict",
                "message": (
                    "Could not generate unique derived identifier(s) after "
                    f"{MAX_GENERATION_ATTEMPTS} conflict-resolution attempts."
                ),
                "metadata": record["metadata"],
            })

            updated_records.append(updated_row)
            continue

        generated_outputs = generated_by_row[row_index]

        updated_row.update(generated_outputs)

        generated_row_count += 1
        generated_identifier_count += len(generated_outputs)

        results.append({
            "row_index": row_index,
            "id_field": target_id_field,
            "action": "derived_generated",
            "identifier": source_identifier,
            "valid": True,
            "error": None,
            "message": f"Generated {len(generated_outputs)} derived identifier(s).",
            "generated_identifiers": generated_outputs,
            "metadata": record["metadata"],
        })

        updated_records.append(updated_row)
        clean_records.append(updated_row.copy())

    error_count = (
        missing_source_count
        + duplicate_source_count
        + source_invalid_count
        + generation_conflict_count
    )

    return {
        "mode": "generation",
        "generation_mode": "derive_from_existing",
        "summary": {
            "total_rows": len(updated_records),
            "generated_row_count": generated_row_count,
            "generated_identifier_count": generated_identifier_count,
            "missing_source_count": missing_source_count,
            "duplicate_source_count": duplicate_source_count,
            "source_invalid_count": source_invalid_count,
            "generation_conflict_count": generation_conflict_count,
            "error_count": error_count,
            "clean_count": len(clean_records),
        },
        "results": results,
        "updated_records": updated_records,
        "clean_records": clean_records,
    }


def build_derived_output_columns(
    raw_generated_outputs: dict[str, str],
    target_id_field: str,
) -> dict[str, str]:
    """
    Convert strategy-level derived outputs into spreadsheet output columns.

    Expected strategy output:
        {
            "EXP": "NRGI-123456_EXP_4829",
            "LIB": "NRGI-123456_LIB_1038"
        }

    Spreadsheet output:
        {
            "identifier_EXP": "NRGI-123456_EXP_4829",
            "identifier_LIB": "NRGI-123456_LIB_1038"
        }
    """

    generated_columns: dict[str, str] = {}

    for output_key, generated_identifier in raw_generated_outputs.items():
        output_column = f"{target_id_field}_{output_key}"
        generated_columns[output_column] = generated_identifier

    return generated_columns

def resolve_derived_generated_conflicts(
    generated_by_row: dict[int, dict[str, str]],
    existing_identifiers: set[str],
    source_identifier_by_row: dict[int, str],
    strategy,
    config: dict,
    target_id_field_by_row: dict[int, str],
    max_attempts: int,
) -> set[int]:
    """
    Resolve conflicts for derived generated identifiers.

    generated_by_row shape:
        {
            0: {
                "identifier_EXP": "NRGI-123456_EXP_4829",
                "identifier_LIB": "NRGI-123456_LIB_1038",
            }
        }

    Conflict rules:
    - Generated derived IDs cannot duplicate existing source IDs.
    - Generated derived IDs cannot duplicate other generated derived IDs.
    - If a row conflicts, regenerate all derived IDs for that row.
    """

    unresolved_conflict_rows: set[int] = set()

    for _ in range(max_attempts):
        conflict_rows = find_derived_generated_conflict_rows(
            generated_by_row=generated_by_row,
            existing_identifiers=existing_identifiers,
        )

        if not conflict_rows:
            return set()

        unresolved_conflict_rows = conflict_rows

        for row_index in conflict_rows:
            source_identifier = source_identifier_by_row[row_index]
            target_id_field = target_id_field_by_row[row_index]

            raw_generated_outputs = strategy.generate_derived_identifiers(
                source_identifier,
                config,
            )

            generated_by_row[row_index] = build_derived_output_columns(
                raw_generated_outputs,
                target_id_field,
            )

    return find_derived_generated_conflict_rows(
        generated_by_row=generated_by_row,
        existing_identifiers=existing_identifiers,
    )


def find_derived_generated_conflict_rows(
    generated_by_row: dict[int, dict[str, str]],
    existing_identifiers: set[str],
) -> set[int]:
    """
    Find rows whose derived generated identifiers conflict.

    Checks the full generated identifier values, not just the modifier number.
    """

    conflict_rows: set[int] = set()

    generated_identifier_to_rows: dict[str, list[int]] = {}

    for row_index, generated_outputs in generated_by_row.items():
        for generated_identifier in generated_outputs.values():
            if generated_identifier in existing_identifiers:
                conflict_rows.add(row_index)

            generated_identifier_to_rows.setdefault(
                generated_identifier,
                [],
            ).append(row_index)

    for rows in generated_identifier_to_rows.values():
        if len(rows) > 1:
            sorted_rows = sorted(rows)

            # Keep the first row and regenerate later conflicting rows.
            later_duplicate_rows = sorted_rows[1:]

            for row_index in later_duplicate_rows:
                conflict_rows.add(row_index)

    return conflict_rows

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

def add_warnings_to_message(message: str, warnings: list[str])-> str:
    if not warnings:
        return message
    return f"{message} Warning: {' '.join(warnings)}"