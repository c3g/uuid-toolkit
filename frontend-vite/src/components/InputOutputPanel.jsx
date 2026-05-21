function InputOutputPanel({
  idName,
  setIdName,
  outputIdField,
  setOutputIdField,
}) {
  return (
    <div className="panel">
      <div className="panel-title">
        Input / Output <span>ⓘ</span>
      </div>

      <label className="field-label">ID Column Name</label>
      <input
        className="input"
        value={idName}
        onChange={(event) => setIdName(event.target.value)}
        placeholder="uuid or identifier"
      />

      <label className="field-label">Output ID Field optional</label>
      <input
        className="input"
        value={outputIdField}
        onChange={(event) => setOutputIdField(event.target.value)}
        placeholder="e.g., generated_uuid"
      />
    </div>
  );
}

export default InputOutputPanel;