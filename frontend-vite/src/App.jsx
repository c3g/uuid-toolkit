import {
  Navigate,
  Route,
  Routes,
} from "react-router-dom";

import DashboardLayout from "./layouts/DashboardLayout.jsx";
import ToolkitPage from "./pages/ToolkitPage.jsx";
import DatabaseManagementPage from "./pages/DatabaseManagementPage.jsx";
import UserManagementPage from "./pages/UserManagementPage.jsx";
import { useAuth } from "./context/useAuth.js";

function App() {
  const { isAdmin } = useAuth();

  return (
    <Routes>
      <Route element={<DashboardLayout />}>
        <Route
          index
          element={
            <Navigate
              to="/toolkit"
              replace
            />
          }
        />

        <Route
          path="toolkit"
          element={<ToolkitPage />}
        />

        <Route
          path="database"
          element={
            isAdmin ? (
              <DatabaseManagementPage />
            ) : (
              <Navigate to="/toolkit" replace />
            )
          }
        />

        <Route
          path="users"
          element={
            isAdmin ? (
              <UserManagementPage />
            ) : (
              <Navigate to="/toolkit" replace />
            )
          }
        />

        <Route
          path="*"
          element={
            <Navigate
              to="/toolkit"
              replace
            />
          }
        />
      </Route>
    </Routes>
  );
}

export default App;