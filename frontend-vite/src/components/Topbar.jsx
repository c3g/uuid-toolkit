import profileImage from "../assets/profile.svg"
function Topbar(){
    return(
        <header className="topbar">
            <div>
                <strong>UUID Toolkit / Dashboard</strong>
            </div>
            
            <div className="topbar-user">
                <button className="profile-button">
                    <img src={profileImage} alt="User Profile" />
                </button>
            </div>
        </header>
    )
}
export default Topbar;