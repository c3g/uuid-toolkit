import uploadIcon from "../assets/icons/upload.svg";

function UploadPanel({file, setFile, loading}){
    return (
        <section className="upload-panel">
            {/*Upload section */}
            <div className="upload-box">
            <p className="upload-title">Upload File</p>

            <div className="upload-input-row">
                <label className="file-upload-button">
                    <img src={uploadIcon} alt="Upload Icon" className="upload-button-icon"/>
                    Choose File
                    <input
                        type="file"
                        accept=".csv,.json,.xlsx"
                        onChange={(e) => setFile(e.target.files[0])}
                        hidden
                    />
                </label>

                <span className="file-upload-name">{file ? file.name : "No file chosen"}</span>
            </div>
            
            <p className="upload-help">Supports CSV, JSON and XLSX files.</p>
            </div>

            <div className="file-info-box">
            <p className="file-info-title">Selected File:</p>

            {file ? (
                <>
                <p className="file-name-display">{file.name}</p>
                <p className="file-status">File is ready</p>
                </>
            ):(
                <p className="file-placeholder">No file selected yet</p>
            )}
            </div>

            <div className="run-box">
            <button type="submit" className="run-button" disabled={loading}>{loading ? "Running..." : "Run"}</button>
            <p className="run-help">Run the current configuration on the uploaded file.</p>
            </div>
        </section> 
    )
}
export default UploadPanel;
