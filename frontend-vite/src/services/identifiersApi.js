import {
  apiRequest,
} from "./apiClient.js";

/*
 * Load stored identifier records.
 *
 * A selected project is more specific than a strategy,
 * so the project filter takes priority.
 */
export function fetchIdentifiers({
  projectId = "",
  strategyName = "",
} = {}) {
  const parameters =
    new URLSearchParams();

  if (projectId !== "") {
    parameters.set(
      "project_id",
      String(projectId)
    );
  } else if (strategyName !== "") {
    parameters.set(
      "strategy_name",
      strategyName
    );
  }

  const query = parameters.toString();

  return apiRequest(
    `/api/identifier_database${
      query ? `?${query}` : ""
    }`
  );
}

/*
 * Delete one database row using its internal
 * IdentifierRegistry primary key.
 */
export function deleteIdentifierRow(
  identifierId
) {
  return apiRequest(
    `/api/database-management/identifiers/row/${
      encodeURIComponent(identifierId)
    }?confirm=true`,
    {
      method: "DELETE",
    }
  );
}

/*
 * Delete rows with an exact identifier value.
 *
 * projectId is optional. When omitted, every matching
 * occurrence across all projects is deleted.
 */
export function deleteIdentifiersByValue({
  identifierValue,
  projectId = "",
}) {
  const parameters =
    new URLSearchParams();

  parameters.set(
    "identifier_value",
    identifierValue.trim()
  );

  if (projectId !== "") {
    parameters.set(
      "project_id",
      String(projectId)
    );
  }

  parameters.set("confirm", "true");

  return apiRequest(
    `/api/database-management/identifiers/value?${parameters.toString()}`,
    {
      method: "DELETE",
    }
  );
}

/*
 * Delete every identifier belonging to one project.
 * The project itself remains.
 */
export function deleteProjectIdentifiers(
  projectId
) {
  return apiRequest(
    `/api/database-management/identifiers/project/${
      encodeURIComponent(projectId)
    }?confirm=true`,
    {
      method: "DELETE",
    }
  );
}

/*
 * Delete every identifier under one strategy.
 * Project Tags remain.
 */
export function deleteStrategyIdentifiers(
  strategyName
) {
  return apiRequest(
    `/api/database-management/identifiers/strategy/${
      encodeURIComponent(strategyName)
    }?confirm=true`,
    {
      method: "DELETE",
    }
  );
}

/*
 * Delete every identifier while keeping Project Tags.
 */
export function deleteAllIdentifiers() {
  return apiRequest(
    "/api/database-management/identifiers/all?confirm=true",
    {
      method: "DELETE",
    }
  );
}