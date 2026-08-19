import { useState, useEffect } from "react";
import ConfigPanel from "../components/ConfigPanel.jsx";
import UploadPanel from "../components/UploadPanel.jsx";
import ResultPanel from "../components/ResultPanel.jsx";
import ErrorPanel from "../components/ErrorPanel.jsx";
import EmptyResultState from "../components/EmptyResultState.jsx";
import RunConfirmationModal from "../components/RunConfirmationModal.jsx";
import "../App.css";

import {
    API_BASE_URL,
} from "../services/apiClient.js";

import {
    fetchProjects,
} from "../services/projectsApi.js";

/*Max visible rows in the preview table */
const MAX_VISIBLE_ROWS = 20;

function ToolkitPage() {
  /* Core app state */
  const [mode, setMode] = useState("validate");
  const [strategy, setStrategy] = useState("CPHI");
  const [file, setFile] = useState(null);
  const [result, setResult] = useState(null);

  /* CPHI / PCGL state */
  const [entity_type, setEntity_type] = useState("");
  const [project_code, setProject_code] = useState("");
  const [variant, setVariant] = useState("");
  const [variants, setVariants] = useState([]);

  /* Input / output state */
  const [idColumn, setIdColumn] = useState("identifier");
  const [outIdColumn, setOutIdColumn] = useState("");
  const [sheetName, setSheetName] = useState("");

  /* UUID state */
  const [uuidVersion, setUuidVersion] = useState("4");

  /* Custom format state */
  const [customPrefixMode, setCustomPrefixMode] = useState("random");
  const [customPrefixType, setCustomPrefixType] = useState("letters");
  const [customPrefixLength, setCustomPrefixLength] = useState("4");
  const [customFixedPrefix, setCustomFixedPrefix] = useState("");
  const [customConnector, setCustomConnector] = useState("-");
  const [customSuffixType, setCustomSuffixType] = useState("numeric");
  const [customSuffixLength, setCustomSuffixLength] = useState("6");

  /* UI state */
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  /* Run confirmation popup state */
  const [showRunConfirmation, setShowRunConfirmation] = useState(false);
  const [runConfirmationData, setRunConfirmationData] = useState(null);

  /* Database values */
  const [projects, setProjects] = useState([]);
  const [projectId, setProjectId] = useState("");
  const [projectsLoading, setProjectsLoading] = useState(false)

  /*Database save states */
  const [saveLoading, setSaveLoading] = useState(false);
  const [saveResult, setSaveResult] = useState(null);


  /* Derived values */
  const outIdName = outIdColumn.trim() || idColumn.trim() || "identifier";

  const resultRows = result?.results || [];
  const cleanRows = resultRows.filter((row) => row.valid === true);
  const incorrectRows =
  resultRows.filter(
    (row) => row.valid === false
  );
  const visible_rows = resultRows.slice(0, MAX_VISIBLE_ROWS);

  /*Derived values for database */
  const cleanIdentifiersForDatabase =
  getCleanIdentifiersForDatabase(result);

  const selectedProject = projects.find(
    (project) =>
      String(project.id) === String(projectId)
  );

  const saveDestinationName =
    selectedProject?.name ||
    `Unassigned (${strategy})`;

  const metadataKeys = Array.from(
    new Set(
      resultRows.flatMap((row) => Object.keys(row.metadata || {}))
    )
  );
  const generatedIdentifierKeys = Array.from(
    new Set(
      resultRows.flatMap((row) =>
        Object.keys(row.generated_identifiers || {})
      )
    )
  );

  /*
  * Clear results from the previous run before changing
  * a setting that affects validation or generation.
  */
  function updateConfiguration(
    stateSetter,
    newValue
  ) {
    setResult(null);
    setError("");
    setSaveResult(null);

    stateSetter(newValue);
  }

  /*Loading the projects for each strategy whenever strategy changes */
  useEffect(() => {
    let cancelled = false;

    async function loadProjects() {
        setProjectsLoading(true);

        try {

            const projectData = await fetchProjects(strategy);

            if (!cancelled) {
                setProjects(projectData);
            }
        } catch (error) {
            console.error(error);

            if (!cancelled) {
                setProjects([]);
            }
        } finally {
            if (!cancelled) {
                setProjectsLoading(false);
            }
        }
    }

    if (strategy) {
        loadProjects();
    } 

    return () => {
        cancelled = true;
    };
  }, [strategy]);

  function handleStrategyChange(newStrategy) {
    setProjects([]);
    setProjectId("");

    updateConfiguration(
      setStrategy,
      newStrategy
    );
  }

  /*Database Helpers */

  function getCleanIdentifiersForDatabase(pipelineResult) {
    const identifiers = new Set();

    for (const row of pipelineResult?.results || []) {
      if (row.valid !== true) {
        continue;
      }

      const generatedIdentifiers = Object.values(
        row.generated_identifiers || {}
      )
        .filter(
          (value) => typeof value === "string"
        )
        .map((value) => value.trim())
        .filter(Boolean);

      /*
      * Derived PCGL generation can produce several IDs
      * from one row. Save the generated IDs instead of
      * the source/base ID.
      */
      if (generatedIdentifiers.length > 0) {
        for (
          const generatedIdentifier
          of generatedIdentifiers
        ) {
          identifiers.add(generatedIdentifier);
        }

        continue;
      }

      /*
      * Validation and fill-missing generation normally
      * use row.identifier.
      */
      if (
        typeof row.identifier === "string" &&
        row.identifier.trim() !== ""
      ) {
        identifiers.add(row.identifier.trim());
      }
    }

        return Array.from(identifiers);
    }

  /* File helpers */
  function getFileType(filename) {
    const extension = filename.split(".").pop().toLowerCase();

    if (extension == "csv") {
      return "csv";
    }

    if (extension == "json") {
      return "json";
    }

    if (extension == "xlsx") {
      return "xlsx";
    }

    return "";
  }

  /* Config helpers */
  function buildConfig() {
    if (strategy == "UUID") {
      return {
        version: Number(uuidVersion),
      };
    }

    if (strategy == "CPHI") {
      return {
        project_code: project_code || null,
        entity_type: entity_type || "sample",
      };
    }

    if (strategy === "PCGL") {
      const baseConfig = {
        project_code: project_code,
        entity_type: entity_type || "sample",
      };

      if (mode === "generate")
        return {
          ...baseConfig,
          variants:variants,
        }
      return {
        ...baseConfig,
        variant: variant||"",
      };
    }

    if (strategy == "CUSTOM") {
      const baseConfig = {
        prefix_mode: customPrefixMode,
        connector: customConnector,
        suffix_type: customSuffixType,
        suffix_length: customSuffixLength,
      };

      if (customPrefixMode == "fixed") {
        return {
          ...baseConfig,
          fixed_prefix: customFixedPrefix,
        };
      }

      return {
        ...baseConfig,
        prefix_type: customPrefixType,
        prefix_length: customPrefixLength,
      };
    }

    return {};
  }

  function validateForm() {
    if (!idColumn.trim()) {
      return "Please enter the ID column name.";
    }

    if (!file) {
      return "Please upload a file.";
    }

    const fileType = getFileType(file.name);

    if (!fileType) {
      return "Unsupported file type, please choose a CSV, JSON, or a xlsx file.";
    }

    if (!strategy) {
      return "Please choose a UUID format/strategy.";
    }

    if (strategy == "CPHI" || strategy == "PCGL") {
      if (!entity_type || entity_type == "") {
        return "Please choose between patient ID or sample ID.";
      }

      if (!project_code) {
        return "Please choose a project code.";
      }
    }

    return "";
  }

  /* Run confirmation helpers */
  function shouldShowRunConfirmation() {
    const normalizedEntityType = (entity_type || "sample")
      .trim()
      .toLocaleLowerCase();

    const strategyUsesEntity = strategy === "CPHI" || strategy === "PCGL";

    return strategyUsesEntity && normalizedEntityType !== "sample";
  }

  function buildRunConfirmation() {
    const selectedProject = projects.find(
      (project) => String(project.id) === String(projectId)
    );
    return {
      mode: mode === "validate" ? "Validate" : "Generate",
      strategy: strategy,
      projectTag: selectedProject?.name || "No project tag",
      fileName: file.name || "No file selected",
      config: buildConfig(),
      inputIdColumn: idColumn || "identifier",
      outputIdColumn: outIdName,
      sheetName: sheetName.trim() || "Active Sheet",
    };
  }

  /* Submit / run handlers */
  async function handleSubmit(event) {
    event.preventDefault();

    setError("");
    setResult(null);

    const validationError = validateForm();

    if (validationError) {
      setError(validationError);
      return;
    }

    if (shouldShowRunConfirmation()) {
      setRunConfirmationData(buildRunConfirmation());
      setShowRunConfirmation(true);
      return;
    }

    runRequest();
  }

  async function runRequest() {
    setError("");
    setResult(null);
    setSaveResult(null);

    const endpoint = mode === "validate" ? "/api/validate" : "/api/generate";

    const formData = new FormData();

    formData.append("file", file);
    formData.append("strategy_name", strategy);
    formData.append("config_json", JSON.stringify(buildConfig()));
    formData.append("id_name", idColumn || "");
    formData.append("output_id_field", outIdName || idColumn || "");
    if (projectId !== ""){
      formData.append("project_id", projectId);
    }

    if (sheetName.trim() !== "") {
      formData.append("sheet_name", sheetName.trim());
    }

    console.log({
      endpoint,
      file: file.name,
      strategy_name: strategy,
      config_json: buildConfig(),
      id_name: idColumn,
      output_id_field: outIdName,
      project_id: projectId || null,
    });

    try {
      setLoading(true);

      const response = await fetch(`${API_BASE_URL}${endpoint}`, {
        method: "POST",
        body: formData,
      });

      const data = await response.json();

      if (!response.ok) {
        throw new Error(data.detail || "Something went wrong.");
      }

      setResult(data);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  }

  async function saveCleanIdentifiers() {
    const identifiers =
      getCleanIdentifiersForDatabase(result);

    if (identifiers.length === 0) {
      setError(
        "There are no clean identifiers to save to the database."
      );
      return;
    }

    const confirmed = window.confirm(
      `Save ${identifiers.length} clean identifier${
        identifiers.length === 1 ? "" : "s"
      } to ${saveDestinationName}?`
    );

    if (!confirmed) {
      return;
    }

    const payload = {
      strategy_name: strategy,
      project_id:
        projectId === ""
          ? null
          : Number(projectId),
      identifiers: identifiers,
    };

    try {
      setSaveLoading(true);
      setSaveResult(null);
      setError("");

      const response = await fetch(
        `${API_BASE_URL}/api/identifier_database/save`,
        {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
          },
          body: JSON.stringify(payload),
        }
      );

      const data = await response.json();

      if (!response.ok) {
        const errorMessage =
          typeof data.detail === "string"
            ? data.detail
            : "The identifiers could not be saved.";

        throw new Error(errorMessage);
      }

      setSaveResult(data);

      /*
        * Saving without a selected Project Tag may create
        * a new Unassigned project. Reload the project list
        * so it appears in the dropdown.
        */
      if (projectId === "") {
        const projectsResponse = await fetch(
          `${API_BASE_URL}/api/projects?strategy_name=${encodeURIComponent(
            strategy
          )}`
        );

        if (projectsResponse.ok) {
          const refreshedProjects =
            await projectsResponse.json();

          setProjects(refreshedProjects);
        }
      }
    } catch (err) {
      setError(
        err instanceof Error
          ? err.message
          : "The identifiers could not be saved."
      );
    } finally {
      setSaveLoading(false);
    }
  }

  function handleConfirmRun() {
    setShowRunConfirmation(false);
    setRunConfirmationData(null);
    runRequest();
  }

  function handleCancelRun() {
    setShowRunConfirmation(false);
    setRunConfirmationData(null);
  }

  /* Download helpers */
  function flattenRow(row) {
    return {
      row_index: row.row_index,
      [outIdName]: row.identifier,
      status: row.valid ? "Valid" : "Invalid",
      message: row.message || "",
      error: row.error || "",
      ...(row.metadata || {}),
    };
  }
  function removeInternalDownloadFields(row) {
    const cleanRow = { ...row };

    delete cleanRow.id_field;

    return cleanRow;
  }

  function convertRowsToCsv(rows, shouldFlatten = true) {
    if (!rows || rows.length === 0) {
      return "";
    }

    const rowsForCsv = shouldFlatten
      ? rows.map(flattenRow).map(removeInternalDownloadFields)
      : rows.map(removeInternalDownloadFields);

    const headers = Array.from(
      new Set(rowsForCsv.flatMap((row) => Object.keys(row)))
    );

    const csvLines = [
      headers.join(","),
      ...rowsForCsv.map((row) =>
        headers
          .map((header) => {
            const value = row[header] ?? "";
            const safeValue =
              typeof value === "object" ? JSON.stringify(value) : value;

            const escapedValue = String(safeValue).replaceAll('"', '""');
            return `"${escapedValue}"`;
          })
          .join(",")
      ),
    ];

    return csvLines.join("\n");
  }

  /* Download handlers */

  function downloadCsv(rows, filename, shouldFlatten = true) {
    const csvString = convertRowsToCsv(rows, shouldFlatten);

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
    if (result?.updated_records) {
      downloadCsv(result.updated_records, "all_results.csv", false);
      return;
    }

    downloadCsv(resultRows, "all_results.csv", true);
  }

  function downloadCleanRows() {
    if (result?.clean_records) {
      downloadCsv(result.clean_records, "clean_rows.csv", false);
      return;
    }

    downloadCsv(cleanRows, "clean_rows.csv", true);
  }
  function downloadIncorrectRows() {
  downloadCsv(
    incorrectRows,
    "incorrect_rows.csv",
    true
  );
}

  return (
    <>
        <div className="page-header">
        <h1>Validate / Generate IDs</h1>

        <p>
            Upload a CSV, JSON, or XLSX file to validate or generate
            unique identifiers for your datasets.
        </p>
        </div>

        <form
        className="toolkit-form"
        onSubmit={handleSubmit}
        >
        <ConfigPanel
          mode={mode}
          setMode={(value) =>
            updateConfiguration(
              setMode,
              value
            )
          }

          strategy={strategy}
          setStrategy={handleStrategyChange}

          projects={projects}
          projectId={projectId}
          setProjectId={(value) =>
            updateConfiguration(
              setProjectId,
              value
            )
          }
          projectsLoading={projectsLoading}
          

          entity_type={entity_type}
          setEntity_type={(value) =>
            updateConfiguration(
              setEntity_type,
              value
            )
          }

          project_code={project_code}
          setProject_code={(value) =>
            updateConfiguration(
              setProject_code,
              value
            )
          }

          variant={variant}
          setVariant={(value) =>
            updateConfiguration(
              setVariant,
              value
            )
          }

          variants={variants}
          setVariants={(value) =>
            updateConfiguration(
              setVariants,
              value
            )
          }

          idColumn={idColumn}
          setIdColumn={(value) =>
            updateConfiguration(
              setIdColumn,
              value
            )
          }

          outIdColumn={outIdColumn}
          setOutIdColumn={(value) =>
            updateConfiguration(
              setOutIdColumn,
              value
            )
          }

          uuidVersion={uuidVersion}
          setUuidVersion={(value) =>
            updateConfiguration(
              setUuidVersion,
              value
            )
          }

          sheetName={sheetName}
          setSheetName={(value) =>
            updateConfiguration(
              setSheetName,
              value
            )
          }

          customPrefixMode={customPrefixMode}
          setCustomPrefixMode={(value) =>
            updateConfiguration(
              setCustomPrefixMode,
              value
            )
          }

          customPrefixType={customPrefixType}
          setCustomPrefixType={(value) =>
            updateConfiguration(
              setCustomPrefixType,
              value
            )
          }

          customPrefixLength={
            customPrefixLength
          }
          setCustomPrefixLength={(value) =>
            updateConfiguration(
              setCustomPrefixLength,
              value
            )
          }

          customFixedPrefix={customFixedPrefix}
          setCustomFixedPrefix={(value) =>
            updateConfiguration(
              setCustomFixedPrefix,
              value
            )
          }

          customConnector={customConnector}
          setCustomConnector={(value) =>
            updateConfiguration(
              setCustomConnector,
              value
            )
          }

          customSuffixType={customSuffixType}
          setCustomSuffixType={(value) =>
            updateConfiguration(
              setCustomSuffixType,
              value
            )
          }

          customSuffixLength={
            customSuffixLength
          }
          setCustomSuffixLength={(value) =>
            updateConfiguration(
              setCustomSuffixLength,
              value
            )
          }
        />

        <UploadPanel
            file={file}
            setFile={setFile}
            loading={loading}
        />
        </form>

        <ErrorPanel
        message={error}
        onClose={() => setError("")}
        />

        {result ? (
        <ResultPanel
            mode={mode}
            result={result}
            resultRows={resultRows}
            visible_rows={visible_rows}
            metadataKeys={metadataKeys}
            generatedIdentifierKeys={generatedIdentifierKeys}
            outIdName={outIdName}
            maxVisibleRows={MAX_VISIBLE_ROWS}
            downloadAllRows={downloadAllRows}
            downloadCleanRows={downloadCleanRows}
            downloadIncorrectRows={downloadIncorrectRows}

            saveCleanIdentifiers={saveCleanIdentifiers}
            saveLoading={saveLoading}
            saveResult={saveResult}
            cleanIdentifierCount={
            cleanIdentifiersForDatabase.length
            }
            saveDestinationName={saveDestinationName}
        />
        ) : (
        <EmptyResultState />
        )}

        <RunConfirmationModal
        isOpen={showRunConfirmation}
        data={runConfirmationData}
        onConfirm={handleConfirmRun}
        onCancel={handleCancelRun}
        loading={loading}
        />
    </>
    );
}

export default ToolkitPage;