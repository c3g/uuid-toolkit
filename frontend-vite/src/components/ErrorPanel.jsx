import errorIcon from "../assets/icons/error_msg.svg";

function ErrorPanel({message, onClose}){
    if (!message){
        return null;
    }
    return (
        <div className="error-panel">
            <div className="error-content">
                <div className="error-icon">
                    <img src={errorIcon} alt="Error Icon"/>
                </div>
                <div>
                    <strong>Something went wrong</strong>
                    <p>{message}</p>
                </div>
            </div>

            {onClose && (
                <button type="button" className="error-close-button" onClick={onClose}>
                    x
                </button>
            )}
        </div>
    )
}
export default ErrorPanel;