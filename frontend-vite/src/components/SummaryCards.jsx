import totalIcon from "../assets/icons/total.png";
import validIcon from "../assets/icons/valid.png";
import invalidIcon from "../assets/icons/error.png";
import duplicateIcon from "../assets/icons/duplicate.png";
import cleanIcon from "../assets/icons/clean.png";

function SummaryCards({summary}){
    return(
        <section className="preview-grid">
            <div className="summary-card total-rows">
                <div className="summary-icon">
                <img src={totalIcon} alt="Total rows icon"/>
                </div>
                <div className="summary-content">
                <strong>Total Rows:</strong>
                <p>{summary.total_rows}</p>
                </div>
            </div>
            <div className="summary-card valid-rows">
                <div className="summary-icon">
                <img src={validIcon} alt="Valid rows icon"/>
                </div>

                <div className="summary-content">
                <strong>Valid Rows:</strong>
                <p>{summary.valid_count}</p>
                </div>
            </div>
            <div className="summary-card invalid-rows">
                <div className="summary-icon">
                <img src={invalidIcon} alt="Invalid rows icon"/>
                </div>
                <div className="summary-content">
                <strong>Invalid Rows:</strong>
                <p>{summary.invalid_count}</p>
                </div>
            </div>
            <div className="summary-card duplicated-rows">
                <div className="summary-icon">
                <img src={duplicateIcon} alt="Duplicated rows icon"/>
                </div>
                <div className="summary-content">
                <strong>Duplicated Rows:</strong>
                <p>{summary.duplicate_count}</p>
                </div>
            </div>
            <div className="summary-card clean-rows">
                <div className="summary-icon">
                <img src={cleanIcon} alt="Clean rows icon"/>
                </div>
                <div className="summary-content">
                <strong>Clean Rows:</strong>
                <p>{summary.clean_count}</p>
                </div>
            </div>
        </section>
    )
}
export default SummaryCards;