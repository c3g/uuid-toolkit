import profileImage from "../assets/profile.svg"
import { useAuth } from "../context/useAuth.js";

function Topbar(){
    const { user, logout } = useAuth();

    return(
        <header className="topbar">
            <div>
                <strong>UUID Toolkit / Dashboard</strong>
            </div>

            <div className="topbar-user">
                {user && (
                    <span className="topbar-user-name">
                        Signed in as {user.name || user.email}
                    </span>
                )}

                <img
                    src={profileImage}
                    alt="User Profile"
                    className="profile-icon"
                />

                <button
                    className="profile-button"
                    onClick={logout}
                >
                    Sign out
                </button>
            </div>
        </header>
    )
}
export default Topbar;