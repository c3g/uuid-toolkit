function DownloadActions({ downloadAllRows, downloadCleanRows}){
    return(
        <div className="download-actions">
            <button type="button" onClick={downloadAllRows}>
                Download All Rows
            </button>

            <button type="button" onClick={downloadCleanRows}>
                Download Clean Rows Only
            </button>
            </div>
    )
}
export default DownloadActions