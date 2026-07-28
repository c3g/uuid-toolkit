import {
  Navigate,
  Route,
  Routes,
} from "react-router-dom";

import DashboardLayout from "./layouts/DashboardLayout.jsx";
import ToolkitPage from "./pages/ToolkitPage.jsx";
import DatabaseManagementPage from "./pages/DatabaseManagementPage.jsx";

function App() {
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
            <DatabaseManagementPage />
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