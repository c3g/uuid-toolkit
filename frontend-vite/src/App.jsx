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
  const [uuidVersion, setUuidVersion]   = useState("4");
  /* Adding and Error State */
  const [error, setError]               = useState("");
  const [loading, setLoading]           = useState(false);


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

  const metadataKeys = Array.from(
    new Set(
      resultRows.flatMap((row) => Object.keys(row.metadata || {}))
    )
  );

  return(
    <div className="app-layout">
      <Sidebar />

      <div className="main-area">
        <Topbar />

        <main className="content">
          <h1>Validate / Generate IDs</h1>
          <p>This is simply the MVP version, 
            afterward I will add the file upload, 
            backend connection, results and styling
          </p>

          <form className="basic-panel" onSubmit={handleSubmit}>
            <label>
              Mode
              <select value={mode} onChange={(e) => setMode(e.target.value)}>
                <option value="validate">Validate IDs</option>
                <option value="generate">Generate IDs</option>

              </select>

            </label>

            <label>
              Identifier Strategy
              <select value={strategy} onChange={(e)=> setStrategy(e.target.value)}>
                <option value="UUID">UUID</option>
                <option value="CPHI">CPHI</option>
              </select>
            </label>

            <label>
              ID Column Name:
              <input type="text" value={idColumn} onChange={(e) => setIdColumn(e.target.value)} placeholder="identifier" />

            </label>

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

            <div className="file-run-row">

              <label className="file-upload">
                Upload File
                <input type="file" accept=".csv,.json,.xlsx" onChange={(e) => setFile(e.target.files[0])} />

              </label>

              <button type="submit" className="run-button" disabled={loading}>{loading ? "Running..." : "Run"}</button>
            </div>

            {file && (
              <p className="file-name">
                Selected file: <strong>{file.name}</strong>
              </p>
            )}
          </form>

          {error && (
            <div className="error-panel">
              <strong>Error:</strong>{error}
            </div>
          )}
          {result && (
            <section className="preview-panel">
              <h2>{mode === "validate" ? "Validation Result" : "Generation Result"}</h2>
              {result.summary && (
                <div className="summary-grid">
                  <div>Total Rows: {result.summary.total_rows}</div>
                  <div>Valid Rows: {result.summary.valid_count}</div>
                  <div>Invalid Rows: {result.summary.invalid_count}</div>
                  <div>Duplicated Rows: {result.summary.duplicate_count}</div>
                  <div>Cleaned Rows: {result.summary.clean_count}</div>
                </div>
              )}
              {resultRows.length >0 && (
                <div className="table-wrapper">
                  <table className="result-table">
                    <thead>
                      <tr>
                        <th>Row #</th>
                        <th>ID Field</th>
                        <th>Identifier</th>
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

              <p>This shows what the front end remembers</p>
              <pre>{JSON.stringify(result,null,2)}</pre>
            </section>
          )}
        </main>
      </div>
    </div>
  )

}
export default App;
