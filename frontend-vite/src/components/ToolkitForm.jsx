import ModeSelector from "./ModeSelector.jsx";
import StrategySelector from "./StrategySelector.jsx";
import ConfigurationPanel from "./ConfigurationPanel.jsx";
import InputOutputPanel from "./InputOutputPanel.jsx";
import OptionsPanel from "./OptionsPanel.jsx";

function ToolkitForm(props) {
  return (
    <section className="form-card">
      <ModeSelector
        mode={props.mode}
        setMode={props.setMode}
      />

      <StrategySelector
        strategyName={props.strategyName}
        setStrategyName={props.setStrategyName}
      />

      <ConfigurationPanel
        strategyName={props.strategyName}
        uuidVersion={props.uuidVersion}
        setUuidVersion={props.setUuidVersion}
        projectCode={props.projectCode}
        setProjectCode={props.setProjectCode}
        entityType={props.entityType}
        setEntityType={props.setEntityType}
        variant={props.variant}
        setVariant={props.setVariant}
      />

      <InputOutputPanel
        idName={props.idName}
        setIdName={props.setIdName}
        outputIdField={props.outputIdField}
        setOutputIdField={props.setOutputIdField}
      />

      <OptionsPanel
        skipExisting={props.skipExisting}
        setSkipExisting={props.setSkipExisting}
        dryRun={props.dryRun}
        setDryRun={props.setDryRun}
      />
    </section>
  );
}

export default ToolkitForm;