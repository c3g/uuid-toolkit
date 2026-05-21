function Sidebar() {
  return (
    <aside className="sidebar">
      <div className="brand">
        <div className="brand-mark">✣</div>
        <div>
          <div className="brand-name">C3G</div>
          <div className="brand-subtitle">
            The Council for Inclusive Capitalism with The Global Goals
          </div>
        </div>
      </div>

      <nav className="nav-menu">
        <a className="nav-item" href="#">
          <span>⌂</span>
          Home
        </a>

        <a className="nav-item active" href="#">
          <span>🛡</span>
          Validate / Generate IDs
        </a>

        <a className="nav-item" href="#">
          <span>⚙</span>
          Settings
        </a>

        <a className="nav-item" href="#">
          <span>⌘</span>
          API Docs
        </a>

        <a className="nav-item" href="#">
          <span>↺</span>
          History
        </a>

        <a className="nav-item" href="#">
          <span>?</span>
          Support
        </a>
      </nav>

      <div className="sidebar-help">
        <div className="help-icon">🛡</div>
        <h3>Need help?</h3>
        <p>Visit our documentation or contact support.</p>
        <button className="secondary-dark-button">Contact Support ↗</button>
      </div>

      <div className="sidebar-user">
        <div className="avatar">AD</div>
        <div>
          <div className="user-name">Alex Doe</div>
          <div className="user-email">admin@c3g.org</div>
        </div>
        <span className="chevron">⌄</span>
      </div>
    </aside>
  );
}

export default Sidebar;