function FileUploadPanel({ mode, file, setFile }) {
  return (
    <section className="upload-card">
      <div className="dropzone">
        <div className="upload-icon">☁</div>
        <p>Drag & drop your file here</p>
        <span>or</span>

        <label className="file-button">
          Choose file
          <input
            type="file"
            accept=".csv,.json,.tsv"
            onChange={(event) => setFile(event.target.files[0])}
          />
        </label>

        <small>Supports CSV, TSV, JSON max 100MB</small>
      </div>

      <div className="selected-file-card">
        {file ? (
          <>
            <div className="file-row">
              <div className="file-icon">📄</div>
              <div>
                <strong>{file.name}</strong>
                <p>{Math.round(file.size / 1024)} KB</p>
              </div>
              <button onClick={() => setFile(null)}>×</button>
            </div>

            <div className="file-ready">✓ File ready</div>
          </>
        ) : (
          <div className="file-empty">No file selected</div>
        )}
      </div>

      <div className="run-panel">
        <button className="primary-button">
          {mode === "generate" ? "Generate IDs" : "Validate IDs"} →
        </button>

        <p>
          This will {mode === "generate" ? "generate IDs for missing rows" : "validate IDs in your file"} and return results.
        </p>
      </div>
    </section>
  );
}

export default FileUploadPanel;