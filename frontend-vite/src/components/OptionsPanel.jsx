function OptionsPanel({
  skipExisting,
  setSkipExisting,
  dryRun,
  setDryRun,
}) {
  return (
    <div className="panel">
      <div className="panel-title">
        Options <span>ⓘ</span>
      </div>

      <label className="checkbox-row">
        <input
          type="checkbox"
          checked={skipExisting}
          onChange={(event) => setSkipExisting(event.target.checked)}
        />
        Skip rows with existing IDs
      </label>

      <label className="checkbox-row">
        <input
          type="checkbox"
          checked={dryRun}
          onChange={(event) => setDryRun(event.target.checked)}
        />
        Use dry run preview only
      </label>
    </div>
  );
}

export default OptionsPanel;