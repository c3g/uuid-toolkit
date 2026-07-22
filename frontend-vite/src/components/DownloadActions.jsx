function DownloadActions({ 
    downloadAllRows, 
    downloadCleanRows,
    saveCleanIdentifiers,
    saveLoading,
    saveCompleted,
    cleanIdentifierCount,
    saveDestinationName,
}){
    const saveDisabled =
        saveLoading ||
        saveCompleted ||
        cleanIdentifierCount === 0;

    function getSaveButtonText() {
        if (saveLoading){
            return "Saving ...";
        }
        if (saveCompleted){
            return "Saved to Database";
        }
        return `Save Clean IDs (${cleanIdentifierCount})`;
    }
    return(
        <div className="download-actions">
            <button type="button" onClick={downloadAllRows}>
                Download All Rows
            </button>

            <button type="button" onClick={downloadCleanRows}>
                Download Clean Rows Only
            </button>
            <button
                type="button"
                className="save-database-button"
                onClick={saveCleanIdentifiers}
                disabled={saveDisabled}
                title={
                    cleanIdentifierCount > 0
                        ? `Save clean identifiers to ${saveDestinationName}`
                        : "No clean identifiers are available to save."
                }
            >
                {getSaveButtonText()}
            </button>
        </div>
    )
}
export default DownloadActions