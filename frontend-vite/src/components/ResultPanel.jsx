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
    downloadIncorrectRows,

    saveCleanIdentifiers,
    saveLoading,
    saveResult,
    cleanIdentifierCount,
    saveDestinationName,
}) {
    return(
        
        <section className="preview-panel">
            <h2>{mode === "validate" ? "Validation Result" : "Generation Result"}</h2>
            
            <DownloadActions
                downloadAllRows={downloadAllRows}
                downloadCleanRows={downloadCleanRows}
                downloadIncorrectRows={downloadIncorrectRows}
                saveCleanIdentifiers={saveCleanIdentifiers}
                saveLoading={saveLoading}
                saveCompleted={saveResult!==null}
                cleanIdentifierCount={cleanIdentifierCount}
                saveDestinationName={saveDestinationName}

            />

            {saveResult && (
                <div 
                    className="database-save-feedback"
                    role="status"
                >
                    <strong>
                        Database update is complete
                    </strong>

                    <p>
                        Saved {saveResult.saved_count} identifier
                        {saveResult.saved_count === 1 ? "" : "s"} to{" "}
                        <strong>
                            {saveResult.project_name}
                        </strong>.
                    </p>

                    {saveResult.already_in_project_count > 0 && (
                        <p>
                            Skipped{" "}
                            {saveResult.already_in_project_count} identifier
                            {saveResult.already_in_project_count === 1
                                ? ""
                                : "s"}{" "}
                            because they already existed in the project.
                        </p>
                    )}
                </div>
            )}
            
            <SummaryCards
                summary={result.summary}
                mode={result.mode || mode}
                generationMode = {result.generation_mode}
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