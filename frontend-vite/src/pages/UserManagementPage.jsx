import {
  useEffect,
  useState,
} from "react";

import {
  deleteUser,
  enrollUser,
  fetchUsers,
  updateUserRole,
} from "../services/usersApi.js";

import "../styles/database-management.css";
import "../styles/user-management.css";

function formatDateTime(value) {
  if (!value) {
    return "—";
  }

  return new Date(value).toLocaleString();
}

function UserManagementPage() {
  const [users, setUsers] =
    useState([]);

  const [usersLoading, setUsersLoading] =
    useState(false);

  const [
    refreshVersion,
    setRefreshVersion,
  ] = useState(0);

  /* Enroll form */
  const [newUserEmail, setNewUserEmail] =
    useState("");

  const [newUserName, setNewUserName] =
    useState("");

  const [newUserRole, setNewUserRole] =
    useState("member");

  const [enrollLoading, setEnrollLoading] =
    useState(false);

  /* Per-row role change / removal */
  const [actionUserId, setActionUserId] =
    useState(null);

  const [actionLoading, setActionLoading] =
    useState(false);

  const [error, setError] = useState("");

  const [successMessage, setSuccessMessage] =
    useState("");

  useEffect(() => {
    let cancelled = false;

    async function loadUsers() {
      try {
        setUsersLoading(true);
        setError("");

        const userData = await fetchUsers();

        if (!cancelled) {
          setUsers(userData);
        }
      } catch (requestError) {
        if (!cancelled) {
          setUsers([]);

          setError(
            requestError instanceof Error
              ? requestError.message
              : "Enrolled users could not be loaded."
          );
        }
      } finally {
        if (!cancelled) {
          setUsersLoading(false);
        }
      }
    }

    loadUsers();

    return () => {
      cancelled = true;
    };
  }, [refreshVersion]);

  function refreshUsers() {
    setRefreshVersion(
      (currentVersion) => currentVersion + 1
    );
  }

  async function handleEnrollUser(event) {
    event.preventDefault();

    setError("");
    setSuccessMessage("");

    const cleanedEmail = newUserEmail.trim();

    if (!cleanedEmail) {
      setError(
        "Please enter the email the person will log in with."
      );
      return;
    }

    try {
      setEnrollLoading(true);

      const createdUser = await enrollUser({
        email: cleanedEmail,
        role: newUserRole,
        name: newUserName,
      });

      setUsers((currentUsers) => [
        ...currentUsers,
        createdUser,
      ]);

      setNewUserEmail("");
      setNewUserName("");
      setNewUserRole("member");

      setSuccessMessage(
        `'${createdUser.email}' enrolled as ${createdUser.role}. ` +
        "They'll be recognized automatically on their next CILogon login."
      );
    } catch (requestError) {
      setError(
        requestError instanceof Error
          ? requestError.message
          : "The user could not be enrolled."
      );
    } finally {
      setEnrollLoading(false);
    }
  }

  async function handleToggleRole(user) {
    setError("");
    setSuccessMessage("");

    const nextRole =
      user.role === "admin" ? "member" : "admin";

    const confirmed = window.confirm(
      `Change ${user.email}'s role from ${user.role} to ${nextRole}?`
    );

    if (!confirmed) {
      return;
    }

    try {
      setActionUserId(user.id);
      setActionLoading(true);

      const updatedUser = await updateUserRole(
        user.id,
        nextRole
      );

      setUsers((currentUsers) =>
        currentUsers.map((existingUser) =>
          existingUser.id === updatedUser.id
            ? updatedUser
            : existingUser
        )
      );

      setSuccessMessage(
        `'${updatedUser.email}' is now ${updatedUser.role}.`
      );
    } catch (requestError) {
      setError(
        requestError instanceof Error
          ? requestError.message
          : "The role could not be changed."
      );
    } finally {
      setActionLoading(false);
      setActionUserId(null);
    }
  }

  async function handleRemoveUser(user) {
    setError("");
    setSuccessMessage("");

    const confirmed = window.confirm(
      `Remove '${user.email}'? They will lose access immediately.`
    );

    if (!confirmed) {
      return;
    }

    try {
      setActionUserId(user.id);
      setActionLoading(true);

      await deleteUser(user.id);

      setUsers((currentUsers) =>
        currentUsers.filter(
          (existingUser) => existingUser.id !== user.id
        )
      );

      setSuccessMessage(
        `'${user.email}' was removed.`
      );
    } catch (requestError) {
      setError(
        requestError instanceof Error
          ? requestError.message
          : "The user could not be removed."
      );
    } finally {
      setActionLoading(false);
      setActionUserId(null);
    }
  }

  return (
    <section className="database-management-page">
      <div className="database-page-heading">
        <div>
          <h1>User Management</h1>

          <p>
            Enroll, promote, or remove people allowed
            to access the toolkit.
          </p>
        </div>

        <button
          type="button"
          className="database-refresh-button"
          onClick={refreshUsers}
          disabled={usersLoading}
        >
          {usersLoading ? "Refreshing..." : "Refresh"}
        </button>
      </div>

      <section className="database-panel">
        <div className="database-panel-heading">
          <div>
            <h2>Enrolled Users</h2>

            <p>
              Everyone currently allowed to log in.
            </p>
          </div>

          <div className="database-result-count">
            <strong>{users.length}</strong>

            <span>
              user{users.length === 1 ? "" : "s"}
            </span>
          </div>
        </div>

        {error && (
          <div className="database-error" role="alert">
            <span>{error}</span>

            <button
              type="button"
              onClick={() => setError("")}
              aria-label="Close error"
            >
              ×
            </button>
          </div>
        )}

        {successMessage && (
          <div className="database-success" role="status">
            <span>{successMessage}</span>

            <button
              type="button"
              onClick={() => setSuccessMessage("")}
              aria-label="Close success message"
            >
              ×
            </button>
          </div>
        )}

        {usersLoading ? (
          <div className="database-state-message">
            Loading enrolled users...
          </div>
        ) : users.length === 0 ? (
          <div className="database-state-message">
            No users are enrolled yet.
          </div>
        ) : (
          <div className="database-table-wrapper">
            <table className="database-table">
              <thead>
                <tr>
                  <th>Email</th>
                  <th>Name</th>
                  <th>Role</th>
                  <th>Enrolled</th>
                  <th>Last Login</th>
                  <th>Action</th>
                </tr>
              </thead>

              <tbody>
                {users.map((user) => {
                  const rowBusy =
                    actionLoading &&
                    actionUserId === user.id;

                  return (
                    <tr key={user.id}>
                      <td>{user.email}</td>

                      <td>{user.name || "—"}</td>

                      <td>
                        <span className="strategy-badge">
                          {user.role}
                        </span>
                      </td>

                      <td>
                        {formatDateTime(user.created_at)}
                      </td>

                      <td>
                        {formatDateTime(user.last_login_at)}
                      </td>

                      <td>
                        <div className="user-row-actions">
                          <button
                            type="button"
                            className="database-secondary-button"
                            onClick={() =>
                              handleToggleRole(user)
                            }
                            disabled={rowBusy}
                          >
                            {user.role === "admin"
                              ? "Make Member"
                              : "Make Admin"}
                          </button>

                          <button
                            type="button"
                            className="project-delete-button"
                            onClick={() =>
                              handleRemoveUser(user)
                            }
                            disabled={rowBusy}
                          >
                            Remove
                          </button>
                        </div>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        )}

        <section className="database-panel project-management-panel">
          <div className="database-panel-heading">
            <div>
              <h2>Enroll a New User</h2>

              <p>
                Reserve access for someone before they've
                ever logged in.
              </p>
            </div>
          </div>

          <div className="project-management-grid">
            <div className="project-create-section">
              <h3>Enroll User</h3>

              <form
                className="project-create-form"
                onSubmit={handleEnrollUser}
              >
                <label className="database-filter-field">
                  <span>Email</span>

                  <input
                    type="email"
                    value={newUserEmail}
                    onChange={(event) =>
                      setNewUserEmail(
                        event.target.value
                      )
                    }
                    placeholder="name@mail.mcgill.ca"
                  />
                </label>

                <label className="database-filter-field">
                  <span>Name — optional</span>

                  <input
                    type="text"
                    value={newUserName}
                    onChange={(event) =>
                      setNewUserName(
                        event.target.value
                      )
                    }
                    placeholder="Optional display name"
                  />
                </label>

                <label className="database-filter-field">
                  <span>Role</span>

                  <select
                    value={newUserRole}
                    onChange={(event) =>
                      setNewUserRole(
                        event.target.value
                      )
                    }
                  >
                    <option value="member">Member</option>
                    <option value="admin">Admin</option>
                  </select>
                </label>

                <button
                  type="submit"
                  className="database-primary-button"
                  disabled={
                    enrollLoading ||
                    newUserEmail.trim() === ""
                  }
                >
                  {enrollLoading
                    ? "Enrolling..."
                    : "Enroll User"}
                </button>
              </form>
            </div>

            <div className="project-list-section">
              <h3>How enrollment works</h3>

              <p className="user-help-text">
                Enrolling someone only reserves their
                access — it doesn't create a CILogon
                account. They need one already, through
                their own institution.
              </p>

              <p className="user-help-text">
                The email entered here must exactly match
                the email their CILogon login reports. The
                first time they log in successfully, this
                app matches that email and remembers them
                automatically from then on.
              </p>

              <p className="user-help-text">
                The last remaining admin can't be demoted
                or removed, so the toolkit is never left
                without one.
              </p>
            </div>
          </div>
        </section>
      </section>
    </section>
  );
}

export default UserManagementPage;
