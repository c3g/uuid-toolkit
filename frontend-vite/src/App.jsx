import { useState, useEffect } from "react";
import Sidebar from "./components/Sidebar.jsx";
import Topbar from "./components/Topbar.jsx";
import ConfigPanel from "./components/ConfigPanel.jsx";
import UploadPanel from "./components/UploadPanel.jsx";
import ResultPanel from "./components/ResultPanel.jsx";
import ErrorPanel from "./components/ErrorPanel.jsx";
import EmptyResultState from "./components/EmptyResultState.jsx";
import "./App.css";

const API_BASE_URL = "http://127.0.0.1:8000";
const MAX_VISIBLE_ROWS = 20;

function App() {
  const [mode, setMode]                 = useState("validate");
  const [strategy, setStrategy]         = useState("CPHI");
  const [file, setFile]                 = useState(null);
  const [result, setResult]             = useState(null);
  const [entity_type, setEntity_type]   = useState("");
  const [project_code, setProject_code] = useState("");
  const [variant, setVariant]           = useState("");
  const [idColumn, setIdColumn]         = useState("identifier");
  const [outIdColumn, setOutIdColumn]   = useState("")
  const [uuidVersion, setUuidVersion]   = useState("4");
  /* Adding and Error State */
  const [error, setError]               = useState("");
  const [loading, setLoading]           = useState(false);

  const outIdName = outIdColumn.trim()|| idColumn.trim() || "identifier";
  const [sheetName, setSheetName] = useState("");

  /*Custom format states */
  const [customPrefixMode, setCustomPrefixMode] = useState("random");
  const [customPrefixType, setCustomPrefixType] = useState("letters");
  const [customPrefixLength, setCustomPrefixLength] = useState("4");
  const [customFixedPrefix, setCustomFixedPrefix] = useState("");
  const [customConnector, setCustomConnector] = useState("-");
  const [customSuffixType, setCustomSuffixType] = useState("numeric");
  const [customSuffixLength, setCustomSuffixLength] = useState("6");

  useEffect(()=> {
    if(result){
      setResult(null);
      setError("");
    }
  }, [
    mode,
    entity_type,
    strategy,
    project_code,
    variant,
    idColumn,
    outIdColumn,
    uuidVersion,
    sheetName,
    customPrefixMode,
    customPrefixLength,
    customFixedPrefix,
    customConnector,
    customSuffixType,
    customSuffixLength,
  ]);


  function getFileType(filename){
    const extension = filename.split(".").pop().toLowerCase();

    if(extension == "csv"){
      return "csv";
    }
    if(extension == "json"){
      return "json";
    }
    if(extension == "xlsx"){
      return "xlsx"
    }
    return "";
  }

  function buildConfig(){
    if (strategy == "UUID"){
      return{
        version: Number(uuidVersion),
      };
    }
    if (strategy == "CPHI"){
      return{
        project_code: project_code || null,
        entity_type: entity_type || "sample",
      }
    }
    if (strategy === "PCGL"){
      return{
        project_code: project_code,
        entity_type: entity_type || "sample",
        variant: variant,
      }
    }
    if (strategy == "CUSTOM"){
      const baseConfig = {
        prefix_mode: customPrefixMode,
        connector: customConnector,
        suffix_type: customSuffixType,
        suffix_length: customSuffixLength,
      };

      if (customPrefixMode == "fixed"){
        return {
          ...baseConfig,
          fixed_prefix:customFixedPrefix,
        };

      }
      return {
        ...baseConfig,
        prefix_type: customPrefixType,
        prefix_length: customPrefixLength,
      }
    };
    
    return{}
  }

  function validateForm(){
    if(!idColumn.trim()){
      return "Please enter the ID column name."
    }
    if (!file){
      return "Please upload a file."
    }
    const fileType = getFileType(file.name);
    if (!fileType){
      return "Unsupported file type, please choose a CSV, JSON, or a xlsx file."
    }

    if (!strategy){
      return "Please choose a UUID format/strategy."
    }
    if(strategy=="CPHI"){
      if(!entity_type ||entity_type==""){
        return "Please choose between patient ID or sample ID."
      }
      if(!project_code){
        return "Please choose a project code."
      }
    }
    return "";
  }
  

  async function handleSubmit(event){
    event.preventDefault();

    setError("");
    setResult("");
    const validationError = validateForm();

    if (validationError) {
      setError(validationError)
      return;
    }

    const endpoint = mode === "validate" ? "/api/validate" : "/api/generate";

    const formData = new FormData();

    formData.append("file", file);
    formData.append("strategy_name", strategy);
    formData.append("config_json",JSON.stringify(buildConfig()));
    formData.append("id_name", idColumn||"");
    formData.append("output_id_field", outIdName||idColumn||"")

    if (sheetName.trim() !== "") {
      formData.append("sheet_name", sheetName.trim());
    }

    console.log({
      endpoint,
      file: file.name,
      strategy_name:strategy,
      config_json: buildConfig(),
      id_name: idColumn,
    })

    try {
      setLoading(true);

      const response = await fetch(`${API_BASE_URL}${endpoint}`, {
        method: "POST",
        body: formData,
      })
      const data = await response.json();

      if(!response.ok){
        throw new Error(data.detail || "Something went wrong.");
      }
      setResult(data);
    }
    catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }

    /*const previewData = {
      endpoint: mode === "validate" ? "/api/validate" : "/api/generate",
      formDataFields:{
        file: file ? file.name : null,
        file_type: file ? getFileType(file.name) :null,
        strategy_name: strategy,
        id_field: idColumn,
        config: buildConfig(),
      },

    };
    setResult(JSON.stringify(previewData, null, 2))*/
  }
  const resultRows = result?.results || []; 
  const cleanRows = resultRows.filter((row)=>row.valid === true);
  const visible_rows = resultRows.slice(0,MAX_VISIBLE_ROWS);
  const metadataKeys = Array.from(
    new Set(
      resultRows.flatMap((row) => Object.keys(row.metadata || {}))
    )
  );

  

  function flattenRow(row) {
    return {
      row_index: row.row_index,
      id_field: row.id_field,
      [outIdName]: row.identifier,
      status: row.valid ? "Valid" : "Invalid",
      message: row.message || "",
      error: row.error || "",
      ...(row.metadata || {}),
    };
  }
  function convertRowsToCsv(rows){
    if (!rows || rows.length === 0){
      return "";
    }
    const flattenedRows = rows.map(flattenRow)

    const headers = Array.from(new Set(flattenedRows.flatMap((row)=> Object.keys(row))));

    const csvLines = [
      headers.join(","),
      ...flattenedRows.map((row) => headers.map((header)=> {
        const value = row[header] ?? "";
        const escapedValue = String(value).replaceAll('"','""');
        return `"${escapedValue}"`
      })
      .join(",")
      ),

    ];
    return csvLines.join("\n");

  }
  function downloadCsv(rows, filename) {
    const csvString = convertRowsToCsv(rows);

    if (!csvString) {
      setError("No rows available to download.");
      return;
    }

    const blob = new Blob(["\uFEFF" + csvString], {
      type: "text/csv;charset=utf-8;",
    });

    const url = URL.createObjectURL(blob);

    const link = document.createElement("a");
    link.href = url;
    link.download = filename;
    link.click();

    URL.revokeObjectURL(url);
  }
  function downloadAllRows() {
    downloadCsv(resultRows, "all_results.csv");
  }

  function downloadCleanRows() {
    downloadCsv(cleanRows, "clean_rows.csv");
  }


  return(
    <div className="app-layout">
      <Sidebar />

      <div className="main-area">
        <Topbar />

        <main className="content">
          <div className="page-header">
            <h1>Validate / Generate IDs</h1>
            <p>
              Upload a CSV, JSON, or XLSX file to validate or generate unique identifiers for your datasets.
            </p>
          </div>
          

          <form className="toolkit-form" onSubmit={handleSubmit}>

            <ConfigPanel
              mode={mode}
              setMode={setMode}
              strategy={strategy}
              setStrategy={setStrategy}
              entity_type={entity_type}
              setEntity_type={setEntity_type}
              project_code={project_code}
              setProject_code={setProject_code}
              variant={variant}
              setVariant={setVariant}
              idColumn={idColumn}
              setIdColumn={setIdColumn}
              outIdColumn={outIdColumn}
              setOutIdColumn={setOutIdColumn}
              uuidVersion={uuidVersion}
              setUuidVersion={setUuidVersion}
              sheetName={sheetName}
              setSheetName={setSheetName}

              customPrefixMode={customPrefixMode}
              setCustomPrefixMode={setCustomPrefixMode}
              customPrefixType={customPrefixType}
              setCustomPrefixType={setCustomPrefixType}
              customPrefixLength={customPrefixLength}
              setCustomPrefixLength={setCustomPrefixLength}
              customFixedPrefix={customFixedPrefix}
              setCustomFixedPrefix={setCustomFixedPrefix}
              customConnector={customConnector}
              setCustomConnector={setCustomConnector}
              customSuffixType={customSuffixType}
              setCustomSuffixType={setCustomSuffixType}
              customSuffixLength={customSuffixLength}
              setCustomSuffixLength={setCustomSuffixLength}
            />

            <UploadPanel
            file={file}
            setFile={setFile}
            loading={loading}
            />
          </form>

          <ErrorPanel message={error} onClose={() => setError("")}/>
          

          {result ? (
            <ResultPanel
              mode={mode}
              result={result}
              resultRows={resultRows}
              visible_rows={visible_rows}
              metadataKeys={metadataKeys}
              outIdName={outIdName}
              maxVisibleRows={MAX_VISIBLE_ROWS}
              downloadAllRows={downloadAllRows}
              downloadCleanRows={downloadCleanRows}
            />
          ): (
            <EmptyResultState/>
          )}
        </main>
      </div>
    </div>
  )

}
export default App;
