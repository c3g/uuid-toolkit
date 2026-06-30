import totalIcon from "../assets/icons/total.png";
import validIcon from "../assets/icons/valid.svg";
import invalidIcon from "../assets/icons/error.png";
import duplicateIcon from "../assets/icons/duplicate.png";
import cleanIcon from "../assets/icons/clean.png";
import missingIcon from "../assets/icons/missing.svg";
import existingIcon from "../assets/icons/existing.svg";
import generatedIcon from "../assets/icons/generated.svg"

function SummaryCard({ className, icon, alt, label, value }) {

    return (
        <div className={`summary-card ${className}`}>
            <div className="summary-icon">
                <img src={icon} alt={alt} />
            </div>

            <div className="summary-content">
                <strong>{label}</strong>
                <p>{value ?? 0}</p>
            </div>
        </div>
    );
}

function SummaryCards({ summary, mode, generationMode }) {
    if (!summary) {
        return null;
    }

    const isValidationMode = mode === "validate" || mode === "validation";
    const isGenerationMode = mode === "generate" || mode === "generation";

    const gridClassName = isGenerationMode
        ? "preview-grid generation-grid"
        : "preview-grid validation-grid"


    const isDerivedGenerationMode =
        isGenerationMode &&
        (
            generationMode === "derive_from_existing" ||
            summary.generated_row_count !== undefined
        );

    const isFillMissingGenerationMode =
        isGenerationMode && !isDerivedGenerationMode;
    return (
        <section className={gridClassName}>
            <SummaryCard
                className="total-rows"
                icon={totalIcon}
                alt="Total rows icon"
                label="Total Rows:"
                value={summary.total_rows}
            />

            {isValidationMode && (
                <>
                    <SummaryCard
                        className="valid-rows"
                        icon={validIcon}
                        alt="Valid rows icon"
                        label="Valid Rows:"
                        value={summary.valid_count}
                    />

                    <SummaryCard
                        className="invalid-rows"
                        icon={invalidIcon}
                        alt="Invalid rows icon"
                        label="Invalid Rows:"
                        value={summary.invalid_count}
                    />

                    <SummaryCard
                        className="duplicated-rows"
                        icon={duplicateIcon}
                        alt="Duplicated rows icon"
                        label="Duplicated Rows:"
                        value={summary.duplicate_count}
                    />

                    <SummaryCard
                        className="clean-rows"
                        icon={cleanIcon}
                        alt="Clean rows icon"
                        label="Clean Rows:"
                        value={summary.clean_count}
                    />
                </>
            )}

            {isFillMissingGenerationMode && (
                <>
                    <SummaryCard
                    className="generated-rows"
                    icon={generatedIcon}
                    alt="Generated rows icon"
                    label="Generated Rows:"
                    value={summary.generated_count}
                    />

                    <SummaryCard
                    className="existing-rows"
                    icon={existingIcon}
                    alt="Existing IDs icon"
                    label="Existing IDs:"
                    value={summary.existing_count}
                    />

                    <SummaryCard
                    className="missing-rows"
                    icon={missingIcon}
                    alt="Missing IDs icon"
                    label="Missing IDs:"
                    value={summary.missing_count}
                    />

                    <SummaryCard
                    className="valid-rows"
                    icon={validIcon}
                    alt="Existing valid IDs icon"
                    label="Existing Valid IDs:"
                    value={summary.existing_valid_count}
                    />

                    <SummaryCard
                    className="invalid-rows"
                    icon={invalidIcon}
                    alt="Existing invalid IDs icon"
                    label="Existing Invalid IDs:"
                    value={summary.existing_invalid_count}
                    />

                    <SummaryCard
                    className="duplicated-rows"
                    icon={duplicateIcon}
                    alt="Duplicated existing IDs icon"
                    label="Duplicated Existing IDs:"
                    value={summary.duplicate_count}
                    />

                    <SummaryCard
                    className="clean-rows"
                    icon={cleanIcon}
                    alt="Clean rows icon"
                    label="Clean Rows:"
                    value={summary.clean_count}
                    />
                </>
            )}

            {isDerivedGenerationMode && (
                <>
                    <SummaryCard
                    className="generated-rows"
                    icon={generatedIcon}
                    alt="Generated rows icon"
                    label="Generated Rows:"
                    value={summary.generated_row_count}
                    />

                    <SummaryCard
                    className="generated-rows"
                    icon={generatedIcon}
                    alt="Generated identifiers icon"
                    label="Generated IDs:"
                    value={summary.generated_identifier_count}
                    />

                    <SummaryCard
                    className="missing-rows"
                    icon={missingIcon}
                    alt="Missing source IDs icon"
                    label="Missing Base IDs:"
                    value={summary.missing_source_count}
                    />

                    <SummaryCard
                    className="invalid-rows"
                    icon={invalidIcon}
                    alt="Invalid source IDs icon"
                    label="Invalid Base IDs:"
                    value={summary.source_invalid_count}
                    />

                    <SummaryCard
                    className="duplicated-rows"
                    icon={duplicateIcon}
                    alt="Duplicate source IDs icon"
                    label="Duplicate Base IDs:"
                    value={summary.duplicate_source_count}
                    />

                    <SummaryCard
                    className="invalid-rows"
                    icon={invalidIcon}
                    alt="Generation conflicts icon"
                    label="Generation Conflicts:"
                    value={summary.generation_conflict_count}
                    />

                    <SummaryCard
                    className="clean-rows"
                    icon={cleanIcon}
                    alt="Clean rows icon"
                    label="Clean Rows:"
                    value={summary.clean_count}
                    />
                </>
            )}
        </section>
    );
}

export default SummaryCards;