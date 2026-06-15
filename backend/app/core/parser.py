import json
import csv
import io

from openpyxl import load_workbook


def parse_file(
        file_bytes: bytes, 
        file_type: str,
        id_name:str | None,
        sheet_name:str |None,
        ):
    if file_type == 'json':
        return json.loads(file_bytes.decode('utf-8-sig'))
    elif file_type == 'csv':
        return list(csv.DictReader(io.StringIO(file_bytes.decode('utf-8-sig'))))
    elif file_type == 'xlsx':
        return parse_xlsx(
            file_bytes,
            id_name=id_name,
            sheet_name=sheet_name,
            )
    else:
        raise ValueError(f"Unsupported file type: {file_type}")
    
def parse_xlsx(
        file_bytes:bytes,
        id_name:str | None,
        sheet_name:str |None,
    ) -> list[dict]:
    
    workbook = load_workbook(
        filename=io.BytesIO(file_bytes),
        data_only=True,
        read_only=True,
    )
    if sheet_name:
        if sheet_name not in workbook.sheetnames:
            raise ValueError(
                f"Sheet '{sheet_name}' was not found."
                f"Available sheets: '{workbook.sheetnames}'"
            )
        worksheet = workbook[sheet_name]

    else:
        worksheet = workbook.active
    

    rows = list(worksheet.iter_rows(values_only=True))

    if not rows:
        raise ValueError("Excel file is empty.")
    
    header_index = detect_header_row(rows,id_name = id_name)
    
    headers = rows[header_index]


    clean_headers = [
        str(header).strip() if header is not None else None
        for header in headers
    ]

    if all(header is None or header == "" for header in clean_headers):
        raise ValueError("Excel file must contain at least one non-empty header.")

    records = []

    for row in rows[header_index+1:]:
        if row is None or all(value is None for value in row):
            continue

        record = {}

        for header, value in zip(clean_headers, row):
            if header is None or header == "":
                continue

            record[header] = normalize_excel_cell(value)

        if any(value not in ("", None) for value in record.values()):
            records.append(record)

    return records

def normalize_excel_cell(value):
    if value == None:
        return ""
    return str(value)

def detect_header_row(
        rows: list[tuple],
        id_name: str | None,
) -> int:
    target_id_name = id_name.strip().lower() if id_name else None

    for index, row in enumerate(rows):
        normalized_values = [
            str(value).strip().lower()
            for value in row
            if value is not None and str(value).strip() != ""
        ]

        if not normalized_values:
            continue

        if target_id_name and target_id_name in normalized_values:
            return index

        # Helpful fallback for Genome Centre sample manifests
        if (
            "sample name" in normalized_values
            and "sample type" in normalized_values
            and "sample kind" in normalized_values
        ):
            return index

        # Generic fallback for simpler spreadsheets
        if any(
            value in {"id", "identifier", "uuid", "uid"}
            for value in normalized_values
        ):
            return index
    #Default state of using the first row as the headers
    return 0




#just testing parser logic here, not part of main codebase
if __name__ == "__main__":
    #Testing Parser logic
    # Example JSON file path (local test only)
    test_file_path = "data/sample1.json"

    # Read file as bytes (simulating upload/API behavior)
    with open(test_file_path, "rb") as f:
        file_bytes = f.read()

    #print raw bytes for debugging
    print("Raw file bytes:")
    print(file_bytes)
    # Call parser
    parsed_output = parse_file(file_bytes, file_type="json")

    # Print results clearly
    print("Parsed output:")
    print(parsed_output)
    print("Type of parsed output:", type(parsed_output))
