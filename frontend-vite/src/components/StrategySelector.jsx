function StrategySelector({ strategyName, setStrategyName }) {
  return (
    <div className="panel">
      <div className="panel-title">
        Identifier Strategy <span>ⓘ</span>
      </div>

      <label className="field-label">Strategy</label>
      <select
        className="input"
        value={strategyName}
        onChange={(event) => setStrategyName(event.target.value)}
      >
        <option value="UUID">UUID</option>
        <option value="CPHI">CPHI</option>
      </select>

      <div className="description-box">
        <span>Description</span>
        {strategyName === "UUID" ? (
          <p>Universally Unique Identifier Version 4</p>
        ) : (
          <p>CPHI identifier with patient/sample support</p>
        )}
        <a href="#">Learn more →</a>
      </div>
    </div>
  );
}

export default StrategySelector;