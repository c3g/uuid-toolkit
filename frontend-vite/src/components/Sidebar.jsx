import favicon from "../assets/c3g_favicon.png"
function Sidebar(){
    return(
        <aside className="sidebar">
            <div>
                <div className="sidebar-brand">
                    <img src={favicon} alt="C3G favicon" className="sidebar-favicon"/>
                    <div className="sidebar-brand-text">
                        <span className="brand-small">Canadian Centre for</span>
                        <span className="brand-large">Computational</span>
                        <span className="brand-large">Genomics</span>
                    </div>
                </div>
                <div className="c3g-info">
                    <p>
                        Bioinformatics analysis, software development, and HPC services for life science research.
                    </p>
                </div>
                
                

                <nav>
                    <button>Home</button>
                    <button className="active">Validate / Generate</button>
                    <button>API Docs</button>
                    <button>History</button>
                    <button>Support</button>
                    <button>Settings</button>
                </nav>
            </div>
            <div className="sidebar-bottom">
                <div className="contact-card">
                    <p className="contact-title">Need help?</p>
                    <p className="contact-text">
                        Visit the C3G website for more information.
                    </p>
                    <a className="contact-button" 
                    href="https://computationalgenomics.ca/contact/"
                    target="_blank"
                    rel="noreferrer"
                    >
                        Contact Us
                    </a>

                </div>

                <p className="developer-credit">Developed by Johnny Weng Lin</p>
            </div>
        </aside>
    )
}
export default Sidebar;