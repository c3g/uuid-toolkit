function RunConfirmationModal({
    isOpen,
    data,
    onConfirm,
    onCancel,
    loading,
}) {
    if (!isOpen||!data){
        return null;
    }

    const configEntries = Object.entries(data.config||{});

    return(
        <div className="modal-backdrop" onClick={onCancel}>
            <div    
                className="run-confirmation-modal"
                role="dialog"
                aria-modal="true"
                onClick={(event)=> event.stopPropagation()}
            >
                <div className="modal-intro-card">
                    <h2>Confirm Non-Sample Run</h2>

                    <p className="modal-warning-text">
                        You selected an entity sample type that is not a sample. Please review your settings and confirm that the entity type you chose is correct. 
                        If you are unsure about which to choose please review the question icon next to the entity type or use the contact us button.
                    </p>
                </div>

                <div className="modal-section">
                    <h3> Run Settings</h3>

                    <div className="confirmation-row">
                        <span>Mode</span>
                        <strong>{data.mode}</strong>
                    </div>
                    <div className="confirmation-row">
                        <span>Strategy</span>
                        <strong>{data.strategy}</strong>
                    </div>
                    <div className="confirmation-row">
                        <span>File</span>
                        <strong>{data.fileName}</strong>
                    </div>
                </div>

                <div className="modal-section">
                    <h3>Configuration</h3>

                    {configEntries.map(([key,value])=> (
                        <div className="confirmation-row" key={key}>
                            <span>{key}</span>
                            <strong>{value === "" || value == null ? "None" : value}</strong>
                        </div>
                    ))}
                </div>

                <div className="modal-section">
                    <h3>Input/Output</h3>

                    <div className="confirmation-row">
                        <span>Input ID column</span>
                        <strong>{data.inputIdColumn}</strong>
                    </div>
                    <div className="confirmation-row">
                        <span>Output ID column</span>
                        <strong>{data.outputIdColumn}</strong>
                    </div>
                    <div className="confirmation-row">
                        <span>Excel Sheet</span>
                        <strong>{data.sheetName}</strong>
                    </div>
                </div>

                <div className="modal-actions">
                    <button 
                        type="button"
                        className="modal-cancel-button"
                        onClick={onCancel}
                        disabled={loading}
                    >
                        Cancel
                    </button>

                    <button
                        type="button"
                        className="modal-confirm-button"
                        onClick={onConfirm}
                        disabled={loading}
                    >
                        {loading ? "Running ...": "Confirm and Run"}
                    </button>
                </div>
            </div>

        </div>
    )
}

export default RunConfirmationModal;