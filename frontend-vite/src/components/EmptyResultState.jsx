import emptyIcon from "../assets/icons/pending.svg";


function EmptyResultState(){
    return(
        <section className="empty-result-panel">
            <div className="empty-result-icon">
                <img src={emptyIcon} alt="empty table icon"/>
            </div>

            <div>
                <h2>No results yet</h2>
                <p>
                    Configure your identifier settings, upload a file, then run validation or generation to see row-level results here.
                </p>
            </div>
        </section>
    )
}
export default EmptyResultState;