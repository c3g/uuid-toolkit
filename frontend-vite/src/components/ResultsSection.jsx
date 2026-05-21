import SummaryCards from "./SummaryCards.jsx";
import ResultsTabs from "./ResultsTabs.jsx";

function ResultsSection({ result }) {
  if (!result) {
    return null;
  }

  return (
    <section className="results-card">
      <div className="results-header">
        <div>
          <h2>Results</h2>
          <span className="status-pill success">{result.status}</span>
          <span className="muted">Completed in {result.processingTime}</span>
        </div>

        <div className="download-actions">
          <button className="outline-button">⇩ Download Clean Records</button>
          <button className="outline-button">⇩ Download Report JSON</button>
          <button className="outline-button">⇩ Download Full Result JSON</button>
        </div>
      </div>

      <SummaryCards summary={result.summary} />

      <ResultsTabs results={result.results} />
    </section>
  );
}

export default ResultsSection;