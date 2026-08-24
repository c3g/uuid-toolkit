import { useEffect, useState } from "react";

import { apiRequest } from "../services/apiClient.js";
import { AuthContext } from "./auth-context.js";

export function AuthProvider({ children }) {
  const [user, setUser] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let cancelled = false;

    apiRequest("/api/auth/me")
      .then((data) => {
        if (!cancelled) {
          setUser(data);
        }
      })
      .catch(() => {
        // Not signed in, or the session expired mid-visit. The backend
        // gate already blocks unauthenticated page loads, so seeing this
        // here means the session died after the page was served -- send
        // the browser back through the gate to get a fresh CILogon login.
        if (!cancelled) {
          window.location.href = "/";
        }
      })
      .finally(() => {
        if (!cancelled) {
          setLoading(false);
        }
      });

    return () => {
      cancelled = true;
    };
  }, []);

  async function logout() {
    await apiRequest("/api/auth/logout", { method: "POST" });

    // Full navigation, not client-side routing, so the backend gate
    // re-evaluates from scratch and redirects to CILogon again.
    window.location.href = "/";
  }

  const value = {
    user,
    loading,
    isAdmin: user?.role === "admin",
    logout,
  };

  return (
    <AuthContext.Provider value={value}>
      {children}
    </AuthContext.Provider>
  );
}
