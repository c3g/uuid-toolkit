import { NavLink } from "react-router-dom";

import favicon from "../assets/c3g_favicon.png";

/*Insert your own API base URL into the .env file once out of development */
const API_BASE_URL =
  import.meta.env.VITE_API_BASE_URL ||
  "http://127.0.0.1:8000";

function Sidebar() {
  function getNavLinkClass({ isActive }) {
    return isActive
      ? "sidebar-nav-link active"
      : "sidebar-nav-link";
  }

  return (
    <aside className="sidebar">
      <div>
        <div className="sidebar-brand">
          <img
            src={favicon}
            alt="C3G favicon"
            className="sidebar-favicon"
          />

          <div className="sidebar-brand-text">
            <span className="brand-small">
              Canadian Centre for
            </span>

            <span className="brand-large">
              Computational
            </span>

            <span className="brand-large">
              Genomics
            </span>
          </div>
        </div>

        <div className="c3g-info">
          <p>
            Bioinformatics analysis, software development,
            and HPC services for life science research.
          </p>
        </div>

        <nav
          className="sidebar-navigation"
          aria-label="Main navigation"
        >
          <NavLink
            to="/toolkit"
            className={getNavLinkClass}
          >
            Validate / Generate
          </NavLink>

          <NavLink
            to="/database"
            className={getNavLinkClass}
          >
            Database Management
          </NavLink>

          <a
            className="sidebar-nav-link"
            href={`${API_BASE_URL}/docs`}
            target="_blank"
            rel="noreferrer"
          >
            API Docs
          </a>
        </nav>
      </div>

      <div className="sidebar-bottom">
        <div className="contact-card">
          <p className="contact-title">
            Need help?
          </p>

          <p className="contact-text">
            Visit the C3G website for more information.
          </p>

          <a
            className="contact-button"
            href="https://computationalgenomics.ca/contact/"
            target="_blank"
            rel="noreferrer"
          >
            Contact Us
          </a>
        </div>

        <p className="developer-credit">
          Developed by Johnny Weng Lin
        </p>
      </div>
    </aside>
  );
}

export default Sidebar;