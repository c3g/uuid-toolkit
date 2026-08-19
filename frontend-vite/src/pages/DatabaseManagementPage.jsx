import {
  useEffect,
  useMemo,
  useState,
} from "react";

import {
  deleteAllIdentifiers,
  deleteIdentifierRow,
  deleteIdentifiersByValue,
  deleteProjectIdentifiers,
  deleteStrategyIdentifiers,
  fetchIdentifiers,
} from "../services/identifiersApi.js";

import {
  createProject,
  deleteProject,
  fetchProjects,
} from "../services/projectsApi.js";

import "../styles/database-management.css";

const PROJECT_STRATEGIES = [
  "UUID",
  "CPHI",
  "PCGL",
  "CUSTOM",
];

function DatabaseManagementPage() {
  /* Data returned by the backend */
  const [identifiers, setIdentifiers] =
    useState([]);

  const [projects, setProjects] =
    useState([]);
  /* Project Tag creation */
  const [
    newProjectStrategy,
    setNewProjectStrategy,
  ] = useState("CPHI");

  const [
    newProjectName,
    setNewProjectName,
  ] = useState("");

  const [
    newProjectDescription,
    setNewProjectDescription,
  ] = useState("");

  const [
    projectCreateLoading,
    setProjectCreateLoading,
  ] = useState(false);

  /* User-selected filters */
  const [
    strategyFilter,
    setStrategyFilter,
  ] = useState("");

  const [
    projectFilter,
    setProjectFilter,
  ] = useState("");

  const [
    searchText,
    setSearchText,
  ] = useState("");

  /* Request state */
  const [
    identifiersLoading,
    setIdentifiersLoading,
  ] = useState(false);

  const [
    projectsLoading,
    setProjectsLoading,
  ] = useState(false);

  const [error, setError] =
    useState("");

  /*
   * Changing this number causes the identifier-loading
   * effect to run again.
   */
  const [
    refreshVersion,
    setRefreshVersion,
  ] = useState(0);

  /* Download state */
    const [
    downloadLoading,
    setDownloadLoading,
    ] = useState(false);

    /* Delete controls */
    const [
    deleteMode,
    setDeleteMode,
    ] = useState("identifier");

    const [
    deleteRowId,
    setDeleteRowId,
    ] = useState("");

    const [
    deleteIdentifierValue,
    setDeleteIdentifierValue,
    ] = useState("");

    const [
    deleteIdentifierProjectId,
    setDeleteIdentifierProjectId,
    ] = useState("");

    const [
    deleteProjectId,
    setDeleteProjectId,
    ] = useState("");

    const [
    deleteStrategyName,
    setDeleteStrategyName,
    ] = useState("");

    const [
    deleteLoading,
    setDeleteLoading,
    ] = useState(false);

    const [
    successMessage,
    setSuccessMessage,
    ] = useState("");

    const [
    clearAllConfirmation,
    setClearAllConfirmation,
    ] = useState("");

  /*
   * Load every Project Tag once when the page opens.
   */
  useEffect(() => {
    let cancelled = false;

    async function loadProjects() {
      try {
        setProjectsLoading(true);

        const projectData =
          await fetchProjects();

        if (!cancelled) {
          setProjects(projectData);
        }
      } catch (requestError) {
        if (!cancelled) {
          setProjects([]);

          setError(
            requestError instanceof Error
              ? requestError.message
              : "Project Tags could not be loaded."
          );
        }
      } finally {
        if (!cancelled) {
          setProjectsLoading(false);
        }
      }
    }

    loadProjects();

    return () => {
      cancelled = true;
    };
  }, []);

  /*
   * Load identifiers whenever the database filters
   * change or the user presses Refresh.
   */
  useEffect(() => {
    let cancelled = false;

    async function loadIdentifiers() {
      try {
        setIdentifiersLoading(true);
        setError("");

        const identifierData =
          await fetchIdentifiers({
            projectId: projectFilter,
            strategyName: strategyFilter,
          });

        if (!cancelled) {
          setIdentifiers(identifierData);
        }
      } catch (requestError) {
        if (!cancelled) {
          setIdentifiers([]);

          setError(
            requestError instanceof Error
              ? requestError.message
              : "Identifiers could not be loaded."
          );
        }
      } finally {
        if (!cancelled) {
          setIdentifiersLoading(false);
        }
      }
    }

    loadIdentifiers();

    return () => {
      cancelled = true;
    };
  }, [
    strategyFilter,
    projectFilter,
    refreshVersion,
  ]);

  /*
   * Create a lookup table:
   *
   * project ID -> complete project object
   */
  const projectsById = useMemo(
    () =>
      new Map(
        projects.map((project) => [
          String(project.id),
          project,
        ])
      ),
    [projects]
  );

  /*
   * Only show projects belonging to the currently
   * selected strategy.
   */
  const availableProjects = useMemo(
    () =>
      projects.filter(
        (project) =>
          strategyFilter === "" ||
          project.strategy_name ===
            strategyFilter
      ),
    [
      projects,
      strategyFilter,
    ]
  );

  /*Show only project tags that can be deleted*/
  const deletableProjects = useMemo(
    () =>
      projects.filter(
        (project) =>
          project.name
            ?.trim()
            .toLowerCase() !== "unassigned"
      ),
    [projects]
  );

  /*
   * Build strategy options from the Project Tags.
   * This avoids hard-coding CPHI, PCGL, UUID, etc.
   */
  const strategyOptions = useMemo(
    () =>
      Array.from(
        new Set(
          projects
            .map(
              (project) =>
                project.strategy_name
            )
            .filter(Boolean)
        )
      ).sort(),
    [projects]
  );

  /*
   * Search is performed in the browser after the
   * backend database filters have been applied.
   */
  const visibleIdentifiers = useMemo(
    () => {
      const normalizedSearch =
        searchText
          .trim()
          .toLowerCase();

      if (!normalizedSearch) {
        return identifiers;
      }

      return identifiers.filter(
        (identifier) => {
          const project =
            projectsById.get(
              String(
                identifier.project_id
              )
            );

          const searchableValues = [
            identifier.id,
            identifier.identifier_value,
            identifier.strategy_name,
            project?.name,
          ];

          return searchableValues.some(
            (value) =>
              String(value ?? "")
                .toLowerCase()
                .includes(
                  normalizedSearch
                )
          );
        }
      );
    },
    [
      identifiers,
      projectsById,
      searchText,
    ]
  );

  function handleStrategyChange(event) {
    setStrategyFilter(
      event.target.value
    );

    /*
     * The previously selected project may belong to
     * another strategy, so clear it.
     */
    setProjectFilter("");
  }

  function refreshIdentifiers() {
    setRefreshVersion(
      (currentVersion) =>
        currentVersion + 1
    );
  }

    function createDatabaseDownloadRows(rows) {
        return rows.map((identifier) => {
            const project = projectsById.get(
            String(identifier.project_id)
            );

            return {
            database_row: identifier.id,
            identifier: identifier.identifier_value,
            strategy_name: identifier.strategy_name,
            project_id: identifier.project_id,
            project_name:
                project?.name || "Unknown Project",
            };
        });
        }

        function convertDatabaseRowsToCsv(rows) {
        if (!rows || rows.length === 0) {
            return "";
        }

        const downloadRows =
            createDatabaseDownloadRows(rows);

        const headers = [
            "database_row",
            "identifier",
            "strategy_name",
            "project_id",
            "project_name",
        ];

        const csvLines = [
            headers.join(","),
            ...downloadRows.map((row) =>
            headers
                .map((header) => {
                const value =
                    row[header] ?? "";

                const escapedValue =
                    String(value).replaceAll(
                    '"',
                    '""'
                    );

                return `"${escapedValue}"`;
                })
                .join(",")
            ),
        ];

        return csvLines.join("\n");
        }

        function downloadDatabaseCsv(
        rows,
        filename
        ) {
        const csvString =
            convertDatabaseRowsToCsv(rows);

        if (!csvString) {
            setError(
            "There are no identifiers to download."
            );
            return;
        }

        const blob = new Blob(
            ["\uFEFF" + csvString],
            {
            type: "text/csv;charset=utf-8;",
            }
        );

        const url =
            URL.createObjectURL(blob);

        const link =
            document.createElement("a");

        link.href = url;
        link.download = filename;
        link.click();

        URL.revokeObjectURL(url);
        }

        function downloadCurrentView() {
        setError("");

        downloadDatabaseCsv(
            visibleIdentifiers,
            "stored_identifiers_current_view.csv"
        );
        }

        async function downloadAllStoredIdentifiers() {
        try {
            setDownloadLoading(true);
            setError("");

            /*
            * Request without filters so this downloads the
            * complete database rather than the current preview.
            */
            const allIdentifiers =
            await fetchIdentifiers();

            downloadDatabaseCsv(
            allIdentifiers,
            "stored_identifiers_all.csv"
            );
        } catch (requestError) {
            setError(
            requestError instanceof Error
                ? requestError.message
                : "Identifiers could not be downloaded."
            );
        } finally {
            setDownloadLoading(false);
        }
    }

    function clearDeleteInputs() {
      setDeleteRowId("");
      setDeleteIdentifierValue("");
      setDeleteIdentifierProjectId("");
      setDeleteProjectId("");
      setDeleteStrategyName("");
    }

    async function handleCreateProject(event) {
        event.preventDefault();

        setError("");
        setSuccessMessage("");

        const cleanedName =
            newProjectName.trim();

        if (!cleanedName) {
            setError(
                "Please enter a Project Tag name."
            );
            return;
        }

        try {
            setProjectCreateLoading(true);

            const createdProject =
                await createProject({
                    name: cleanedName,
                    strategyName:
                        newProjectStrategy,
                    description:
                        newProjectDescription.trim(),
                });

            setProjects(
                (currentProjects) => [
                    ...currentProjects,
                    createdProject,
                ]
            );

            setNewProjectName("");
            setNewProjectDescription("");

            setSuccessMessage(
                `Project Tag '${createdProject.name}' created successfully.`
            );
        } catch (requestError) {
            setError(
                requestError instanceof Error
                    ? requestError.message
                    : "The Project Tag could not be created."
            );
        } finally {
            setProjectCreateLoading(false);
        }
    }

    async function handleDeleteSubmit(event) {
        event.preventDefault();

        setError("");
        setSuccessMessage("");

        let confirmationMessage = "";
        let deleteRequest = null;

        if (deleteMode === "row") {
            const normalizedRowId =
            deleteRowId.trim();

            if (!normalizedRowId) {
            setError(
                "Please enter a database row number."
            );
            return;
            }

            if (
            !Number.isInteger(
                Number(normalizedRowId)
            ) ||
            Number(normalizedRowId) <= 0
            ) {
            setError(
                "The database row number must be a positive integer."
            );
            return;
            }

            confirmationMessage =
            `Delete database row ${normalizedRowId}?`;

            deleteRequest = () =>
            deleteIdentifierRow(
                Number(normalizedRowId)
            );
        }

        if (deleteMode === "identifier") {
            const normalizedIdentifier =
            deleteIdentifierValue.trim();

            if (!normalizedIdentifier) {
            setError(
                "Please enter an identifier value."
            );
            return;
            }

            const selectedProject =
            projects.find(
                (project) =>
                String(project.id) ===
                String(
                    deleteIdentifierProjectId
                )
            );

            if (deleteIdentifierProjectId) {
            confirmationMessage =
                `Delete '${normalizedIdentifier}' from ` +
                `${selectedProject?.name || "the selected project"}?`;
            } else {
            confirmationMessage =
                `Delete every exact occurrence of ` +
                `'${normalizedIdentifier}' across all projects?`;
            }

            deleteRequest = () =>
            deleteIdentifiersByValue({
                identifierValue:
                normalizedIdentifier,
                projectId:
                deleteIdentifierProjectId,
            });
        }

        if (deleteMode === "project") {
            if (!deleteProjectId) {
            setError(
                "Please select a Project Tag."
            );
            return;
            }

            const selectedProject =
            projects.find(
                (project) =>
                String(project.id) ===
                String(deleteProjectId)
            );

            confirmationMessage =
            `Delete every identifier from ` +
            `${selectedProject?.name || "the selected project"}? ` +
            `The Project Tag will remain.`;

            deleteRequest = () =>
            deleteProjectIdentifiers(
                deleteProjectId
            );
        }

        if (deleteMode === "strategy") {
            if (!deleteStrategyName) {
            setError(
                "Please select a strategy."
            );
            return;
            }

            confirmationMessage =
            `Delete every ${deleteStrategyName} identifier ` +
            `from every project? The Project Tags will remain.`;

            deleteRequest = () =>
            deleteStrategyIdentifiers(
                deleteStrategyName
            );
        }

        const confirmed =
            window.confirm(
            confirmationMessage
            );

        if (!confirmed || !deleteRequest) {
            return;
        }

        try {
            setDeleteLoading(true);

            const data =
            await deleteRequest();

            const deletedCount =
            data.identifiers_deleted ??
            (data.deleted === true ? 1 : 0);

            setSuccessMessage(
            `${deletedCount} identifier${
                deletedCount === 1 ? "" : "s"
            } deleted successfully.`
            );

            clearDeleteInputs();
            refreshIdentifiers();
        } catch (requestError) {
            setError(
            requestError instanceof Error
                ? requestError.message
                : "The identifiers could not be deleted."
            );
        } finally {
            setDeleteLoading(false);
        }
    }

    async function handleDeleteProject(projectId) {
        setError("");
        setSuccessMessage("");

        const selectedProject = projects.find(
            (project) =>
                String(project.id) === String(projectId)
        );

        if (!selectedProject) {
            setError(
                "The selected Project Tag could not be found."
            );
            return;
        }

        if (
            selectedProject.name
                ?.trim()
                .toLowerCase() === "unassigned"
        ) {
            setError(
                "The Unassigned Project Tag is system-managed and cannot be deleted."
            );
            return;
        }

        const confirmed = window.confirm(
            `Delete Project Tag '${selectedProject.name}'? ` +
            "All identifiers belonging to this Project Tag will also be deleted."
        );

        if (!confirmed) {
            return;
        }

        try {
            setDeleteLoading(true);

            const data = await deleteProject(
                projectId
            );

            setSuccessMessage(
                `Project Tag '${selectedProject.name}' deleted successfully. ` +
                `${data.identifiers_deleted} identifier${
                    data.identifiers_deleted === 1
                        ? ""
                        : "s"
                } were also deleted.`
            );

            setProjects((currentProjects) =>
                currentProjects.filter(
                    (project) =>
                        String(project.id) !==
                        String(projectId)
                )
            );

            refreshIdentifiers();

        } catch (requestError) {
            setError(
                requestError instanceof Error
                    ? requestError.message
                    : "The Project Tag could not be deleted."
            );
        } finally {
            setDeleteLoading(false);
        }
    }

    async function handleClearAllIdentifiers() {
        setError("");
        setSuccessMessage("");

        if (
            clearAllConfirmation !==
            "CLEAR ALL IDENTIFIERS"
        ) {
            setError(
            "Type CLEAR ALL IDENTIFIERS exactly to confirm."
            );
            return;
        }

        const confirmed =
            window.confirm(
            "Delete every stored identifier? " +
            "Project Tags will remain."
            );

        if (!confirmed) {
            return;
        }

        try {
            setDeleteLoading(true);

            const data =
            await deleteAllIdentifiers();

            setSuccessMessage(
            `${data.identifiers_deleted} identifier${
                data.identifiers_deleted === 1
                ? ""
                : "s"
            } deleted successfully.`
            );

            setClearAllConfirmation("");
            clearDeleteInputs();
            refreshIdentifiers();
        } catch (requestError) {
            setError(
            requestError instanceof Error
                ? requestError.message
                : "The identifiers could not be deleted."
            );
        } finally {
            setDeleteLoading(false);
        }
    }

  return (
    <section className="database-management-page">
      <div className="database-page-heading">
        <div>
          <h1>Database Management</h1>

          <p>
            View, search, and manage identifiers
            currently stored in the database.
          </p>
        </div>

        <button
          type="button"
          className="database-refresh-button"
          onClick={refreshIdentifiers}
          disabled={identifiersLoading}
        >
          {identifiersLoading
            ? "Refreshing..."
            : "Refresh"}
        </button>
      </div>

      <section className="database-panel">
        <div className="database-panel-heading">
          <div>
            <h2>Stored Identifiers</h2>

            <p>
              Filter identifiers by strategy or
              Project Tag.
            </p>
          </div>

          <div className="database-result-count">
            <strong>
              {visibleIdentifiers.length}
            </strong>

            <span>
              identifier
              {visibleIdentifiers.length === 1
                ? ""
                : "s"}
            </span>
          </div>
        </div>

        <div className="database-filters">
          <label className="database-filter-field">
            <span>Search</span>

            <input
              type="search"
              value={searchText}
              onChange={(event) =>
                setSearchText(
                  event.target.value
                )
              }
              placeholder="Search identifiers or projects"
            />
          </label>

          <label className="database-filter-field">
            <span>Strategy</span>

            <select
              value={strategyFilter}
              onChange={
                handleStrategyChange
              }
              disabled={projectsLoading}
            >
              <option value="">
                All strategies
              </option>

              {strategyOptions.map(
                (strategyName) => (
                  <option
                    key={strategyName}
                    value={strategyName}
                  >
                    {strategyName}
                  </option>
                )
              )}
              
            </select>
          </label>

          <label className="database-filter-field">
            <span>Project Tag</span>

            <select
              value={projectFilter}
              onChange={(event) =>
                setProjectFilter(
                  event.target.value
                )
              }
              disabled={projectsLoading}
            >
              <option value="">
                All Project Tags
              </option>

              {availableProjects.map(
                (project) => (
                  <option
                    key={project.id}
                    value={project.id}
                  >
                    {project.name} - {project.strategy_name}
                  </option>
                )
              )}
            </select>
          </label>
        </div>

        <div className="database-action-buttons">
            <button
                type="button"
                className="database-secondary-button"
                onClick={downloadCurrentView}
                disabled={
                visibleIdentifiers.length === 0
                }
            >
                Download Current View
            </button>

            <button
                type="button"
                className="database-secondary-button"
                onClick={
                downloadAllStoredIdentifiers
                }
                disabled={downloadLoading}
            >
                {downloadLoading
                ? "Preparing Download..."
                : "Download All Identifiers"}
            </button>
        </div>

        {error && (
          <div
            className="database-error"
            role="alert"
          >
            <span>{error}</span>

            <button
              type="button"
              onClick={() =>
                setError("")
              }
              aria-label="Close error"
            >
              ×
            </button>
          </div>
        )}
        {successMessage && (
            <div
                className="database-success"
                role="status"
            >
                <span>{successMessage}</span>

                <button
                type="button"
                onClick={() =>
                    setSuccessMessage("")
                }
                aria-label="Close success message"
                >
                ×
                </button>
            </div>
        )}

        {identifiersLoading ? (
          <div className="database-state-message">
            Loading stored identifiers...
          </div>
        ) : visibleIdentifiers.length === 0 ? (
          <div className="database-state-message">
            No identifiers match the selected
            filters.
          </div>
        ) : (
          <div className="database-table-wrapper">
            <table className="database-table">
              <thead>
                <tr>
                  <th>Database Row</th>
                  <th>Identifier</th>
                  <th>Strategy</th>
                  <th>Project Tag</th>
                </tr>
              </thead>

              <tbody>
                {visibleIdentifiers.map(
                  (identifier) => {
                    const project =
                      projectsById.get(
                        String(
                          identifier.project_id
                        )
                      );

                    return (
                      <tr key={identifier.id}>
                        <td>
                          {identifier.id}
                        </td>

                        <td className="identifier-value-cell">
                          {
                            identifier.identifier_value
                          }
                        </td>

                        <td>
                          <span className="strategy-badge">
                            {
                              identifier.strategy_name
                            }
                          </span>
                        </td>

                        <td>
                          {project?.name ||
                            "Unknown Project"}
                        </td>
                      </tr>
                    );
                  }
                )}
              </tbody>
            </table>
          </div>
        )}

        <section className="database-panel project-management-panel">
          <div className="database-panel-heading">
            <div>
              <h2>Manage Project Tags</h2>

              <p>
                Create Project Tags or remove existing
                Project Tags from the database.
              </p>
            </div>
          </div>

          <div className="project-management-grid">

            {/* Create Project Tag */}
            <div className="project-create-section">
              <h3>Create Project Tag</h3>

              <form
                className="project-create-form"
                onSubmit={handleCreateProject}
              >
                <label className="database-filter-field">
                  <span>Strategy</span>

                  <select
                    value={newProjectStrategy}
                    onChange={(event) =>
                      setNewProjectStrategy(
                        event.target.value
                      )
                    }
                  >
                    {PROJECT_STRATEGIES.map(
                      (strategyName) => (
                        <option
                          key={strategyName}
                          value={strategyName}
                        >
                          {strategyName}
                        </option>
                      )
                    )}
                  </select>
                </label>

                <label className="database-filter-field">
                  <span>Project Tag Name</span>

                  <input
                    type="text"
                    value={newProjectName}
                    onChange={(event) =>
                      setNewProjectName(
                        event.target.value
                      )
                    }
                    placeholder="Example: Brain Tumour Study"
                  />
                </label>

                <label className="database-filter-field">
                  <span>Description — optional</span>

                  <textarea
                    value={newProjectDescription}
                    onChange={(event) =>
                      setNewProjectDescription(
                        event.target.value
                      )
                    }
                    placeholder="Optional project description"
                    rows="4"
                  />
                </label>

                <button
                  type="submit"
                  className="database-primary-button"
                  disabled={
                    projectCreateLoading ||
                    newProjectName.trim() === ""
                  }
                >
                  {projectCreateLoading
                    ? "Creating..."
                    : "Create Project Tag"}
                </button>
              </form>
            </div>

            {/* Existing Project Tags */}
            <div className="project-list-section">
              <h3>Existing Project Tags</h3>

              {projectsLoading ? (
                <p className="database-state-message">
                  Loading Project Tags...
                </p>
              ) : projects.length === 0 ? (
                <p className="database-state-message">
                  No Project Tags currently exist.
                </p>
              ) : (
                <div className="database-table-wrapper">
                  <table className="database-table project-table">
                    <thead>
                      <tr>
                        <th>Project Tag</th>
                        <th>Strategy</th>
                        <th>Description</th>
                        <th>Action</th>
                      </tr>
                    </thead>

                    <tbody>
                      {projects.map((project) => {
                        const isUnassigned =
                          project.name
                            ?.trim()
                            .toLowerCase() ===
                          "unassigned";

                        return (
                          <tr key={project.id}>
                            <td>{project.name}</td>

                            <td>
                              <span className="strategy-badge">
                                {project.strategy_name}
                              </span>
                            </td>

                            <td>
                              {project.description ||
                                "—"}
                            </td>

                            <td>
                              {isUnassigned ? (
                                <span className="system-project-label">
                                  System
                                </span>
                              ) : (
                                <button
                                  type="button"
                                  className="project-delete-button"
                                  onClick={() =>
                                    handleDeleteProject(
                                      project.id
                                    )
                                  }
                                  disabled={deleteLoading}
                                >
                                  Delete
                                </button>
                              )}
                            </td>
                          </tr>
                        );
                      })}
                    </tbody>
                  </table>
                </div>
              )}
            </div>

          </div>
        </section>

        <section className="database-panel database-delete-panel">
            <div className="database-panel-heading">
                <div>
                <h2>Manage Stored Identifiers</h2>

                <p>
                    Delete identifiers by database row,
                    identifier value, Project Tag, or strategy.
                </p>
                </div>
            </div>

            <form
                className="database-delete-form"
                onSubmit={handleDeleteSubmit}
            >
                <label className="database-filter-field">
                <span>Delete by</span>

                <select
                    value={deleteMode}
                    onChange={(event) => {
                    setDeleteMode(
                        event.target.value
                    );

                    setError("");
                    setSuccessMessage("");
                    clearDeleteInputs();
                    }}
                >
                    <option value="identifier">
                    Identifier value
                    </option>

                    <option value="row">
                    Database row number
                    </option>

                    <option value="project">
                    Project Tag
                    </option>

                    <option value="strategy">
                    Strategy
                    </option>
                </select>
                </label>

                {deleteMode === "row" && (
                <label className="database-filter-field">
                    <span>Database row number</span>

                    <input
                    type="number"
                    min="1"
                    value={deleteRowId}
                    onChange={(event) =>
                        setDeleteRowId(
                        event.target.value
                        )
                    }
                    placeholder="Example: 42"
                    />
                </label>
                )}

                {deleteMode === "identifier" && (
                <>
                    <label className="database-filter-field">
                    <span>Identifier value</span>

                    <input
                        type="text"
                        value={deleteIdentifierValue}
                        onChange={(event) =>
                        setDeleteIdentifierValue(
                            event.target.value
                        )
                        }
                        placeholder="Example: NRGI-123456"
                    />
                    </label>

                    <label className="database-filter-field">
                    <span>
                        Project Tag — optional
                    </span>

                    <select
                        value={
                        deleteIdentifierProjectId
                        }
                        onChange={(event) =>
                        setDeleteIdentifierProjectId(
                            event.target.value
                        )
                        }
                    >
                        <option value="">
                        All Project Tags
                        </option>

                        {projects.map((project) => (
                        <option
                            key={project.id}
                            value={project.id}
                        >
                            {project.name} —{" "}
                            {project.strategy_name}
                        </option>
                        ))}
                    </select>
                    </label>
                </>
                )}

                {deleteMode === "project" && (
                <label className="database-filter-field">
                    <span>Project Tag</span>

                    <select
                    value={deleteProjectId}
                    onChange={(event) =>
                        setDeleteProjectId(
                        event.target.value
                        )
                    }
                    >
                    <option value="">
                        Select a Project Tag
                    </option>

                    {projects.map((project) => (
                        <option
                        key={project.id}
                        value={project.id}
                        >
                        {project.name} —{" "}
                        {project.strategy_name}
                        </option>
                    ))}
                    </select>
                </label>
                )}

                {deleteMode === "strategy" && (
                <label className="database-filter-field">
                    <span>Strategy</span>

                    <select
                    value={deleteStrategyName}
                    onChange={(event) =>
                        setDeleteStrategyName(
                        event.target.value
                        )
                    }
                    >
                    <option value="">
                        Select a strategy
                    </option>

                    {strategyOptions.map(
                        (strategyName) => (
                        <option
                            key={strategyName}
                            value={strategyName}
                        >
                            {strategyName}
                        </option>
                        )
                    )}
                    </select>
                </label>
                )}

                <button
                type="submit"
                className="database-delete-button"
                disabled={deleteLoading}
                >
                {deleteLoading
                    ? "Deleting..."
                    : "Delete Identifiers"}
                </button>
            </form>

            <div className="database-danger-zone">
                <div>
                <h3>Clear All Identifiers</h3>

                <p>
                    This removes every stored identifier.
                    Project Tags and database tables will remain.
                </p>
                </div>

                <div className="database-danger-controls">
                <label className="database-filter-field">
                    <span>
                    Type CLEAR ALL IDENTIFIERS
                    </span>

                    <input
                    type="text"
                    value={clearAllConfirmation}
                    onChange={(event) =>
                        setClearAllConfirmation(
                        event.target.value
                        )
                    }
                    placeholder="CLEAR ALL IDENTIFIERS"
                    />
                </label>

                <button
                    type="button"
                    className="database-danger-button"
                    onClick={
                    handleClearAllIdentifiers
                    }
                    disabled={deleteLoading}
                >
                    Clear All Identifiers
                </button>
                </div>
            </div>
        </section>
      </section>
    </section>
  );
}

export default DatabaseManagementPage;