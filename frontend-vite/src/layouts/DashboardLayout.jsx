import { Outlet } from "react-router-dom";
import Sidebar from "../components/Sidebar.jsx";
import "../styles/layout.css";
import Topbar from "../components/Topbar.jsx";

function DashboardLayout() {
    return (
        <div className="app-layout">
            <Sidebar />

            <div className="main-area">
                <Topbar />

                <main className="content">
                    <Outlet />
                </main>
            </div>

        </div>
    )
}

export default DashboardLayout;