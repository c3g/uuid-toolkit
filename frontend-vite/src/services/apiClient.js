export const API_BASE_URL =
  import.meta.env.VITE_API_BASE_URL ||
  "http://127.0.0.1:8000";

function getErrorMessage(
  data,
  fallbackMessage
) {
  if (typeof data?.detail === "string") {
    return data.detail;
  }

  if (Array.isArray(data?.detail)) {
    const validationMessages = data.detail
      .map((item) => item?.msg)
      .filter(Boolean);

    if (validationMessages.length > 0) {
      return validationMessages.join(" ");
    }
  }

  if (typeof data?.message === "string") {
    return data.message;
  }

  return fallbackMessage;
}

export async function apiRequest(
  path,
  options = {}
) {
  const response = await fetch(
    `${API_BASE_URL}${path}`,
    options
  );

  const contentType =
    response.headers.get("content-type") || "";

  let data = null;

  if (
    contentType.includes(
      "application/json"
    )
  ) {
    data = await response.json();
  } else {
    const responseText =
      await response.text();

    if (responseText) {
      data = {
        message: responseText,
      };
    }
  }

  /*Checking for other errors and displaying error instead of crashing */
  if (!response.ok) {
    const message = getErrorMessage(
      data,
      `Request failed with status ${response.status}.`
    );

    throw new Error(message);
  }

  return data;
}