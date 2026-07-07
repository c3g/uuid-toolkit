function ResultsTable({
    resultRows,
    visible_rows,
    metadataKeys,
    generatedIdentifierKeys,
    outIdName,
    maxVisibleRows
}){
    return (
        <>
            
            
            {resultRows.length > maxVisibleRows && (
                <p className="table-note">
                Showing first {maxVisibleRows} of {resultRows.length} rows. Download
                the CSV to access all rows.
                </p>
            )}

            {resultRows.length > 0 && (
                <div className="table-wrapper">
                <table className="result-table">
                    <thead>
                    <tr>
                        <th>Row #</th>
                        {/*<th>ID Field</th>*/}
                        <th>{outIdName}</th>
                        {generatedIdentifierKeys.map((key) => (
                            <th key={key}>{key}</th>
                        ))}
                        <th>Status</th>
                        <th>Message</th>

                        {metadataKeys.map((key) => (
                        <th key={key}>{key}</th>
                        ))}
                    </tr>
                    </thead>

                    <tbody>
                    {visible_rows.map((row, index) => (
                        <tr key={index}>
                        <td>{row.row_index}</td>
                        {/*<td>{row.id_field}</td>*/}
                        <td>{row.identifier}</td>

                        {generatedIdentifierKeys.map((key) => (
                            <td key={key}>{row.generated_identifiers?.[key] ?? ""}</td>
                        ))}

                        <td>
                            <span
                            className={
                                row.valid === true
                                ? "status-badge valid"
                                : "status-badge invalid"
                            }
                            >
                            {row.valid === true ? "Valid" : "Invalid"}
                            </span>
                        </td>

                        <td>{row.message || row.error || ""}</td>

                        {metadataKeys.map((key) => (
                            <td key={key}>{row.metadata?.[key] ?? ""}</td>
                        ))}
                        </tr>
                    ))}
                    </tbody>
                </table>
                </div>
            )}
        </>
    )
}
export default ResultsTable;