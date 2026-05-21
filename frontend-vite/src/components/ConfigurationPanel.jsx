function ConfigurationPanel({
  strategyName,
  uuidVersion,
  setUuidVersion,
  projectCode,
  setProjectCode,
  entityType,
  setEntityType,
  variant,
  setVariant,
}) {
  const variantsByEntityType = {
    patient: ["", "SPE"],
    sample: ["", "EXP", "RG", "ANA", "LIB", "WRK"],
  };

  return (
    <div className="panel">
      <div className="panel-title">
        Configuration <span>ⓘ</span>
      </div>

      {strategyName === "UUID" && (
        <>
          <label className="field-label">UUID Version</label>
          <select
            className="input"
            value={uuidVersion}
            onChange={(event) => setUuidVersion(event.target.value)}
          >
            <option value="4">Version 4 (random)</option>
          </select>

          <div className="info-box">
            ⓘ Generates random UUIDs in the standard 8-4-4-4-12 hexadecimal format.
          </div>
        </>
      )}

      {strategyName === "CPHI" && (
        <>
          <label className="field-label">Project Code</label>
          <input
            className="input"
            value={projectCode}
            onChange={(event) => setProjectCode(event.target.value)}
            placeholder="e.g., NRGI"
          />

          <label className="field-label">Entity Type</label>
          <select
            className="input"
            value={entityType}
            onChange={(event) => {
              setEntityType(event.target.value);
              setVariant("");
            }}
          >
            <option value="patient">Patient</option>
            <option value="sample">Sample</option>
          </select>

          <label className="field-label">Variant Optional</label>
          <select
            className="input"
            value={variant}
            onChange={(event) => setVariant(event.target.value)}
          >
            {variantsByEntityType[entityType].map((option) => (
              <option key={option} value={option}>
                {option === "" ? "None" : option}
              </option>
            ))}
          </select>

          <div className="info-box">
            ⓘ Patient and sample IDs share the same base format. Variants are optional.
          </div>
        </>
      )}
    </div>
  );
}

export default ConfigurationPanel;