function Topbar() {
  return (
    <header className="topbar">
      <div></div>

      <div className="topbar-actions">
        <button className="icon-button">?</button>
        <div className="topbar-divider"></div>
        <div className="topbar-user">
          <div className="topbar-avatar">AD</div>
          <span>Alex Doe</span>
          <span>⌄</span>
        </div>
      </div>
    </header>
  );
}

export default Topbar;