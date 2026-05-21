import { useState } from "react";

import Sidebar from "./components/Sidebar.jsx";
import Topbar from "./components/Topbar.jsx";
import ToolkitHeader from "./components/ToolkitHeader.jsx";
import Stepper from "./components/Stepper.jsx";
import ToolkitForm from "./components/ToolkitForm.jsx";
import FileUploadPanel from "./components/FileUploadPanel.jsx";
import ResultsSection from "./components/ResultsSection.jsx";

function App() {
  const [mode, setMode] = useState("validate");
  const [strategyName, setStrategyName] = useState("UUID");
  const [uuidVersion, setUuidVersion] = useState("4");
  const [projectCode, setProjectCode] = useState("NRGI");
  const [entityType, setEntityType] = useState("sample");
  const [variant, setVariant] = useState("");
  const [idName, setIdName] = useState("uuid");
  const [outputIdField, setOutputIdField] = useState("");
  const [skipExisting, setSkipExisting] = useState(true);
  const [dryRun, setDryRun] = useState(false);
  const [file, setFile] = useState(null);

  const mockResult = {
    status: "Completed",
    processingTime: "0.42s",
    summary: {
      total_rows: 5,
      valid_ids: 3,
      invalid_ids: 2,
      clean_records: 3,
      processing_time: "0.42s",
    },
    results: [
      {
        row_index: 1,
        identifier: "550e8400-e29b-41d4-a716-446655440000",
        status: "Valid",
        message: "UUID is valid (version 4)",
        action: "-",
      },
      {
        row_index: 2,
        identifier: "not-a-uuid",
        status: "Invalid",
        message: "Invalid UUID format",
        action: "-",
      },
      {
        row_index: 3,
        identifier: "-",
        status: "Invalid",
        message: "Missing ID",
        action: "-",
      },
      {
        row_index: 4,
        identifier: "123e4567-e89b-12d3-a456-426614174000",
        status: "Valid",
        message: "UUID is valid (version 1)",
        action: "-",
      },
      {
        row_index: 5,
        identifier: "550e8400-e29b-41d4-a716-446655440001",
        status: "Valid",
        message: "UUID is valid (version 4)",
        action: "-",
      },
    ],
  };

  return (
    <div className="app-shell">
      <Sidebar />

      <main className="main-area">
        <Topbar />

        <div className="page-content">
          <ToolkitHeader />
          <Stepper />

          <ToolkitForm
            mode={mode}
            setMode={setMode}
            strategyName={strategyName}
            setStrategyName={setStrategyName}
            uuidVersion={uuidVersion}
            setUuidVersion={setUuidVersion}
            projectCode={projectCode}
            setProjectCode={setProjectCode}
            entityType={entityType}
            setEntityType={setEntityType}
            variant={variant}
            setVariant={setVariant}
            idName={idName}
            setIdName={setIdName}
            outputIdField={outputIdField}
            setOutputIdField={setOutputIdField}
            skipExisting={skipExisting}
            setSkipExisting={setSkipExisting}
            dryRun={dryRun}
            setDryRun={setDryRun}
          />

          <FileUploadPanel
            mode={mode}
            file={file}
            setFile={setFile}
          />

          <ResultsSection result={mockResult} />
        </div>
      </main>
    </div>
  );
}

export default App;