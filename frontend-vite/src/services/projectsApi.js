import {
  apiRequest,
} from "./apiClient.js";

export function fetchProjects(
  strategyName = ""
) {
  const parameters =
    new URLSearchParams();

  if (strategyName) {
    parameters.set(
      "strategy_name",
      strategyName
    );
  }

  const query = parameters.toString();

  return apiRequest(
    `/api/projects${
      query ? `?${query}` : ""
    }`
  );
}

export function createProject({
  name,
  strategyName,
  description = "",
}) {
  const formData = new FormData();

  formData.append(
    "name",
    name.trim()
  );

  formData.append(
    "strategy_name",
    strategyName
  );

  if (description.trim()) {
    formData.append(
      "description",
      description.trim()
    );
  }

  return apiRequest(
    "/api/database-management/projects",
    {
      method: "POST",
      body: formData,
    }
  );
}

export function deleteProject(
    projectId
) {
    return apiRequest(
        `/api/database-management/projects/${projectId}?confirm=true`,
        {
            method: "DELETE",
        }
    );
}
