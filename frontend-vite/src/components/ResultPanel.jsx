import DownloadActions from "./DownloadActions.jsx";
import SummaryCards from "./SummaryCards.jsx";
import ResultsTable from "./ResultsTable.jsx";

function ResultPanel({
    mode,
    result,
    resultRows,
    visible_rows,
    metadataKeys,
    generatedIdentifierKeys,
    outIdName,
    maxVisibleRows,
    downloadAllRows,
    downloadCleanRows,
}) {
    return(
        
        <section className="preview-panel">
            <h2>{mode === "validate" ? "Validation Result" : "Generation Result"}</h2>
            
            <DownloadActions
                downloadAllRows={downloadAllRows}
                downloadCleanRows={downloadCleanRows}
            />
            
            <SummaryCards
                summary={result.summary}
                mode={result.mode || mode}
                generation_mode = {result.generation_mode}
            />
            

            
            <ResultsTable
                resultRows={resultRows}
                visible_rows={visible_rows}
                metadataKeys={metadataKeys}
                generatedIdentifierKeys={generatedIdentifierKeys}
                outIdName={outIdName}
                maxVisibleRows={maxVisibleRows}
            />

            
            {/*
            <p>This shows what the front end remembers</p>
            <pre>{JSON.stringify(result,null,2)}</pre>
            */}
        </section>
            
    )
}
export default ResultPanel