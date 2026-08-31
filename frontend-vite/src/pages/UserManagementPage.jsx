import {
  useEffect,
  useState,
} from "react";

import {
  fetchUsers,
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

  const [error, setError] = useState("");

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

  return (
    <section className="database-management-page">
      <div className="database-page-heading">
        <div>
          <h1>User Management</h1>

          <p>
            Everyone currently allowed to log in.
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

            <p className="user-help-text">
              Enrollment is moving to COManage group
              management — this list is read-only here
              for now.
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
                </tr>
              </thead>

              <tbody>
                {users.map((user) => (
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
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </section>
    </section>
  );
}

export default UserManagementPage;
