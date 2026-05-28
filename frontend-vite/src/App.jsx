import { useState } from "react";
import Sidebar from "./components/Sidebar.jsx";
import Topbar from "./components/Topbar.jsx";
import "./App.css";

const API_BASE_URL = "http://127.0.0.1:8000";

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
        entity_type: entity_type || null,
        variant: variant ||null,
      }
    }
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

  const metadataKeys = Array.from(
    new Set(
      resultRows.flatMap((row) => Object.keys(row.metadata || {}))
    )
  );

  function getStrategyDescription(){
    if(strategy === "UUID"){
      return "Universally unique identifer. 128 bit number for identifying objects or information int he form of a 36 character alphanumerical string. "
    }
    if(strategy === "CPHI"){
      return "CPHI identifier specifications that follow the following structure: XXXX-000000. XXXX: A four character string identifying the project. 000000: six digit ID not encoding any metdata"
    }
    return "Choose a identifier strategy to see its description"
  }

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
          <h1>Validate / Generate IDs</h1>
          

          <form className="toolkit-form" onSubmit={handleSubmit}>

            <section className="config-panel">
              <div className="config-grid">
                {/*Mode */}
                <div className="config-card">
                  <h3>Mode</h3>
                  <div className="mode-button-group">
                    <button
                      type="button"
                      className={mode === "validate"? "mode-button active" : "mode-button"}
                      onClick={() => setMode("validate")}
                    >
                      <strong>Validate</strong>
                      <span>Check IDs and report invalid rows.</span>
                    </button>

                    <button
                      type="button"
                      className={mode === "generate"? "mode-button active" : "mode-button"}
                      onClick={() => setMode("generate")}
                    >
                      <strong>Generate</strong>
                      <span>Generate IDs for missing rows.</span>
                    </button>
                    </div>
                </div>

                {/*Identifier Strategy */}
                <div className="config-card">
                  <h3>Identifier Strategy</h3>
                  <label>
                    <select value={strategy} onChange={(e)=> setStrategy(e.target.value)}>
                      <option value="UUID">UUID</option>
                      <option value="CPHI">CPHI</option>
                    </select>
                  </label>
                  <div className="strategy-description">
                    <strong>Description:</strong>
                    <p>{getStrategyDescription()}</p>
                  </div>
                </div>

                {/*Configuration card */}
                <div className="config-card">
                  <h3>Configuration</h3>

                  {strategy == "UUID" && (
                    <label>
                      UUID Version
                      <select value={uuidVersion} onChange={(e) => setUuidVersion(e.target.value)}>
                        <option value="4">Version 4</option>
                        <option value="7">Version 7</option>
                      </select>
                    </label>
                  )}

                  {strategy == "CPHI" && (
                    <>
                      <label>
                        CPHI Entity Type
                        <select value={entity_type} 
                        onChange={(e) => {
                          setEntity_type(e.target.value); 
                          setVariant("");
                          }}
                        >
                          <option value="">Select a type of CPHI ID</option>
                          <option value="patient">Patient</option>
                          <option value="sample">Sample</option>
                        </select>
                      </label>
                      
                      <label>
                        Project Code
                        {/*These are the list of available project codes. 
                        If new projects are added, add them as an option here */}
                        <select value={project_code} onChange={(e) => setProject_code(e.target.value)}>
                          <option value="">Select a Project Code</option>
                          <option value="NRGI">NRGI</option>
                          <option value="C4RE">C4RE</option>
                          <option value="GSCD">GSCD</option>
                          <option value="GEPM">GEPM</option>
                          <option value="LDPP">LDPP</option>
                          <option value="EPCC">EPCC</option>
                          <option value="INFA">INFA</option>
                          <option value="MOSA">MOSA</option>
                          <option value="CS4C">CS4C</option>
                          <option value="PHNN">PHNN</option>
                          <option value="PGEM">PGEM</option>
                          <option value="G4PR">G4PR</option>
                        </select>
                      </label>
                      {entity_type == "patient" && (
                        <label>
                          Variant
                          <select value={variant} onChange={(e) => setVariant(e.target.value)}>
                            <option value="">None</option>
                            <option value="SPE">SPE</option>

                          </select>
                        </label>
                      )}
                      {entity_type == "sample" && (
                        <label>
                          Variant
                          <select value={variant} onChange={(e) => setVariant(e.target.value)}>
                            <option value="">None</option>
                            <option value="EXP">EXP</option>
                            <option value="LIB">LIB</option>
                            <option value="RG">RG</option>
                            <option value="WRK">WRK</option>
                            <option value="ANA">ANA</option>
                          </select>
                        </label>
                      )}
                    </>
                  )}
                  
                </div>

                {/*Input/Output Card */}
                <div className="config-card">
                  <h3>Input/Output</h3>
                  <label>
                    Input ID Column Name:
                    <input type="text" value={idColumn} onChange={(e) => setIdColumn(e.target.value)} placeholder="identifier" />

                  </label>
                  <label>
                    Output ID Column Name:
                    <input type="text" value={outIdColumn} onChange={(e) => setOutIdColumn(e.target.value)} placeholder={idColumn||"identifier"}/>
                  </label>
                  <p className="output-field-help">Leave empty to use the input column name.</p>
                </div>

                
              </div>
            </section>

            <section className="upload-panel">
              {/*Upload section */}
              <div className="upload-box">
                <p className="upload-title">Upload File</p>

                <div className="upload-input-row">
                  <label className="file-upload-button">
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
          </form>

          {error && (
            <div className="error-panel">
              <strong>Error:</strong>{error}
            </div>
          )}
          {result && (
            <section className="preview-panel">
              <h2>{mode === "validate" ? "Validation Result" : "Generation Result"}</h2>
              
              <div className="download-actions">
                <button type="button" onClick={downloadAllRows}>
                  Download All Rows
                </button>

                <button type="button" onClick={downloadCleanRows}>
                  Download Clean Rows Only
                </button>
              </div>
              
              <section className="preview-grid">
                <div className="total-rows">
                  <strong>Total Rows:</strong>
                  <p>{result.summary.total_rows}</p>
                </div>
                <div className="valid-rows">
                  <strong>Valid Rows:</strong>
                  <p>{result.summary.valid_count}</p>
                </div>
                <div className="invalid-rows">
                  <strong>Invalid Rows:</strong>
                  <p>{result.summary.invalid_count}</p>
                </div>
                <div className="duplicated-rows">
                  <strong>Duplicated Rows:</strong>
                  <p>{result.summary.duplicate_count}</p>
                </div>
                <div className="clean-rows">
                  <strong>Clean Rows:</strong>
                  <p>{result.summary.clean_count}</p>
                </div>
              </section>
              
              {resultRows.length >0 && (
                <div className="table-wrapper">
                  <table className="result-table">
                    <thead>
                      <tr>
                        <th>Row #</th>
                        <th>ID Field</th>
                        <th>{outIdName}</th>
                        <th>Status</th>
                        <th>Message</th>
                        
                        {metadataKeys.map((key) => (
                          <th key={key}>{key}</th>
                        ))}


                      </tr>
                    </thead>
                    <tbody>
                      {resultRows.map((row,index) => (
                        <tr key={index}>
                          <td>{row.row_index}</td>
                          <td>{row.id_field}</td>
                          <td>{row.identifier}</td>
                          <td>{row.valid? "Valid" : "Invalid"}</td>
                          <td>{row.message || row.error || ""}</td>

                          {metadataKeys.map((key) => (
                            <td key={key}>{row.metadata?.[key] ??""}</td>
                          ))}
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>  
              )}
              {/*
              <p>This shows what the front end remembers</p>
              <pre>{JSON.stringify(result,null,2)}</pre>
              */}
            </section>
          )}
        </main>
      </div>
    </div>
  )

}
export default App;
