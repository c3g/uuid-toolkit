import {
  apiRequest,
} from "./apiClient.js";

export function fetchUsers() {
  return apiRequest("/api/users");
}

export function enrollUser({
  email,
  role,
  name = "",
}) {
  const formData = new FormData();

  formData.append(
    "email",
    email.trim()
  );

  formData.append(
    "role",
    role
  );

  if (name.trim()) {
    formData.append(
      "name",
      name.trim()
    );
  }

  return apiRequest(
    "/api/users",
    {
      method: "POST",
      body: formData,
    }
  );
}

export function updateUserRole(
  userId,
  role
) {
  const formData = new FormData();

  formData.append(
    "role",
    role
  );

  return apiRequest(
    `/api/users/${encodeURIComponent(userId)}`,
    {
      method: "PATCH",
      body: formData,
    }
  );
}

export function deleteUser(
  userId
) {
  return apiRequest(
    `/api/users/${encodeURIComponent(userId)}?confirm=true`,
    {
      method: "DELETE",
    }
  );
}
