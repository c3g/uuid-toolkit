import ResultsTable from "./ResultsTable.jsx";

function ResultsTabs({ results }) {
  return (
    <div className="results-tabs">
      <div className="tab-list">
        <button className="tab active">Row-level Results</button>
        <button className="tab">Clean Records (3)</button>
        <button className="tab">Raw Updated Records (5)</button>
      </div>

      <ResultsTable results={results} />

      <div className="table-footer">
        Showing 1 to {results.length} of {results.length} rows
      </div>
    </div>
  );
}

export default ResultsTabs;