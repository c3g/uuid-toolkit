function ModeSelector({ mode, setMode }) {
  return (
    <div className="panel">
      <div className="panel-title">
        Mode <span>ⓘ</span>
      </div>

      <button
        type="button"
        className={mode === "validate" ? "mode-card selected" : "mode-card"}
        onClick={() => setMode("validate")}
      >
        <div className="radio-dot">{mode === "validate" && <span></span>}</div>
        <div>
          <strong>Validate IDs</strong>
          <p>Check IDs and report invalid rows</p>
        </div>
      </button>

      <button
        type="button"
        className={mode === "generate" ? "mode-card selected" : "mode-card"}
        onClick={() => setMode("generate")}
      >
        <div className="radio-dot">{mode === "generate" && <span></span>}</div>
        <div>
          <strong>Generate IDs</strong>
          <p>Generate IDs for missing or invalid rows</p>
        </div>
      </button>
    </div>
  );
}

export default ModeSelector;