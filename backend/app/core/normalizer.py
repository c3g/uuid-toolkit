#Receive input from parser, and normalize data into the format of ID and Metadata
#Metadata is a dictionary of all other fields except the one used for ID, it is not touched throughout the entire process
#If no ID field is found, we set the identifier to be "None"

#global variable for possible identifier headers
POSSIBLE_ID_HEADERS = {
    "id", "ID", "Id", "identifier", 
    "Identifier", "ID_number", "id_number",
    "ID_num", "id_num", "uuid", "UUID", "Uuid",
    "uid", "UID", "Uid"
}

class AmbiguousIDFieldError(Exception):
    pass

# Receive input from parser and normalize data into a consistent format.
#
# Normalized format:
# {
#     "row_index": int,
#     "id_field": str | None,
#     "identifier": str | None,
#     "metadata": dict,
#     "original_record": dict
# }
#
# identifier:
#     The extracted ID value.
#
# id_field:
#     The column/key name where the ID was found.
#     Useful for generation because we need to know where to insert a new ID.
#
# metadata:
#     All fields except the ID field.
#
# original_record:
#     The full original row.
#     Useful for reconstructing output after generation.


def normalize(parsed_data, id_name: str | None = None):
    """
    Normalize parsed JSON/CSV data into a standard row format.

    Parameters
    ----------
    parsed_data:
        Output from parser.py. Expected to be either a dict or list of dicts.

    id_name:
        Optional explicit ID field name.
        Example: "uuid", "id", "identifier".

    Returns
    -------
    list[dict]
        A list of normalized records.
    """

    rows = _coerce_to_rows(parsed_data)

    normalized_records = []

    # Find the actual ID field name.
    # If user provides id_name, use that.
    # If not, try to detect it from the headers.
    if id_name is None:
        id_field = detect_id_field(rows)
    else:
        id_field = resolve_id_field(rows, id_name)

    for row_index, row in enumerate(rows):
        if not isinstance(row, dict):
            raise ValueError(
                f"Row {row_index} must be a dictionary, got {type(row).__name__}."
            )

        # Extract identifier value.
        if id_field is not None and id_field in row:
            raw_identifier = row.get(id_field)
        else:
            raw_identifier = None

        identifier,warnings = normalize_identifier_value(raw_identifier)

        # Metadata contains everything except the ID field.
        metadata = {}

        for key, value in row.items():
            if key != id_field:
                metadata[key] = value

        normalized_record = {
            "row_index": row_index,
            "id_field": id_field,
            "identifier": identifier,
            "metadata": metadata,
            "original_record": row.copy(),
            "warnings": warnings,
        }

        normalized_records.append(normalized_record)

    return normalized_records


def _coerce_to_rows(parsed_data):
    """
    Convert parsed input into a list of row dictionaries.
    """

    if isinstance(parsed_data, dict):
        return [parsed_data]

    if isinstance(parsed_data, list):
        return parsed_data

    raise ValueError(
        f"Unable to normalize data. Expected dict or list, got {type(parsed_data).__name__}."
    )


def normalize_identifier_value(value):
    """
    Convert empty identifiers to None.

    Examples:
        ""      -> None
        "   "   -> None
        None    -> None
        "abc"   -> "abc"
    """
    warnings=[]

    if value is None:
        return None,warnings

    if isinstance(value, str):
        stripped = value.strip()

        if stripped == "":
            if value != "":
                warnings.append("Identifier contained only whitespace and was treated as missing.")
            return None,warnings
        
        if stripped != value:
            warnings.append("Surrounding whitespace was removed beforehand.")

        return stripped, warnings

    return value,warnings


def resolve_id_field(rows: list[dict], id_name: str) -> str:
    """
    Resolve the actual ID field name from user-provided id_name.

    This allows the user to pass "uuid" even if the actual file column is "UUID".

    If the field does not exist in the uploaded file, we still return id_name.
    This is useful for generation because the pipeline can create that column.
    """

    normalized_target = id_name.strip().lower()

    matches = set()

    for row in rows:
        if not isinstance(row, dict):
            continue

        for key in row.keys():
            normalized_key = str(key).strip().lower()

            if normalized_key == normalized_target:
                matches.add(key)

    if len(matches) == 1:
        return next(iter(matches))

    if len(matches) > 1:
        raise AmbiguousIDFieldError(
            f"Multiple fields match the provided ID name '{id_name}': {matches}."
        )

    # If the requested ID field is not present, return id_name anyway.
    # This allows generation to create a new ID column with this name.
    return id_name


def detect_id_field(rows: list[dict]) -> str | None:
    """
    Detect the ID field automatically.

    Detection is case-insensitive, but the returned field name preserves
    the original column/key name from the data.
    """

    id_candidates = set()

    for row in rows:
        if not isinstance(row, dict):
            continue

        for key in row.keys():
            normalized_key = str(key).strip().lower()

            if normalized_key in POSSIBLE_ID_HEADERS:
                id_candidates.add(key)

    if len(id_candidates) == 1:
        return next(iter(id_candidates))

    if len(id_candidates) > 1:
        raise AmbiguousIDFieldError(
            f"Multiple potential ID fields found: {id_candidates}. "
            "Please specify the ID field explicitly."
        )

    return None

#Testing purposes only
if __name__ == "__main__":
    import json

    data_path = "data/sample_data.json"

    with open(data_path, "r") as f:
        parsed_data = json.load(f)

    print("Parsed input:")
    print(parsed_data)
    print()

    try:
        normalized = normalize(parsed_data)
    except AmbiguousIDFieldError as e:
        print("Normalization failed with error:")
        print(e)
        exit(1)

    print("Normalized output:")
    for record in normalized:
        print(record)