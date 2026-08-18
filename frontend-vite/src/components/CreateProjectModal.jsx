import { useState } from "react";


function CreateProjectForm({
  strategy,
  loading,
  error,
  onClose,
  onSubmit,
}) {
  const [projectName, setProjectName] =
    useState("");

  const [description, setDescription] =
    useState("");

  function handleSubmit(event) {
    event.preventDefault();

    const cleanedName = projectName.trim();

    if (!cleanedName) {
      return;
    }

    onSubmit({
      name: cleanedName,
      description: description.trim(),
    });
  }

  return (
    <div className="modal-backdrop">
      <div
        className="create-project-modal"
        role="dialog"
        aria-modal="true"
        aria-labelledby="create-project-title"
      >
        <div className="modal-intro-card">
          <h2 id="create-project-title">
            Create Project Tag
          </h2>

          <p className="modal-warning-text">
            Create a database project for the
            currently selected strategy. The created
            project will be used to determine the
            comparison scope for validation and
            generation.
          </p>
        </div>

        <form onSubmit={handleSubmit}>
          <div
            className={
              "modal-section create-project-fields"
            }
          >
            <label>
              Strategy

              <input
                type="text"
                value={strategy}
                disabled
              />
            </label>

            <label>
              Project Name

              <input
                type="text"
                value={projectName}
                onChange={(event) =>
                  setProjectName(
                    event.target.value
                  )
                }
                placeholder={
                  "Example: Brain Tumour Study"
                }
                autoFocus
              />
            </label>

            <label>
              Description

              <textarea
                value={description}
                onChange={(event) =>
                  setDescription(
                    event.target.value
                  )
                }
                placeholder="Optional description"
                rows="4"
              />
            </label>

            {error && (
              <p className="create-project-error">
                {error}
              </p>
            )}
          </div>

          <div className="modal-actions">
            <button
              type="button"
              className="modal-cancel-button"
              onClick={onClose}
              disabled={loading}
            >
              Cancel
            </button>

            <button
              type="submit"
              className="modal-confirm-button"
              disabled={
                loading ||
                projectName.trim() === ""
              }
            >
              {loading
                ? "Creating..."
                : "Create Project"}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}


function CreateProjectModal({
  isOpen,
  strategy,
  loading,
  error,
  onClose,
  onSubmit,
}) {
  if (!isOpen) {
    return null;
  }

  return (
    <CreateProjectForm
      strategy={strategy}
      loading={loading}
      error={error}
      onClose={onClose}
      onSubmit={onSubmit}
    />
  );
}


export default CreateProjectModal;