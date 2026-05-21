function ResultsTable({ results }) {
  return (
    <div className="table-wrapper">
      <table>
        <thead>
          <tr>
            <th>Row #</th>
            <th>uuid</th>
            <th>Status</th>
            <th>Message</th>
            <th>Action</th>
          </tr>
        </thead>

        <tbody>
          {results.map((row) => (
            <tr key={row.row_index}>
              <td>{row.row_index}</td>
              <td>{row.identifier}</td>
              <td>
                <span
                  className={
                    row.status === "Valid"
                      ? "table-pill valid"
                      : "table-pill invalid"
                  }
                >
                  {row.status}
                </span>
              </td>
              <td>{row.message}</td>
              <td>{row.action}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

export default ResultsTable;