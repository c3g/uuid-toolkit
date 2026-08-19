function ConfigPanel({
    mode,
    setMode,
    strategy,
    setStrategy,

    projects,
    projectId,
    setProjectId,
    projectsLoading,

    entity_type,
    setEntity_type,
    project_code,
    setProject_code,
    variant,
    setVariant,
    variants,
    setVariants,
    idColumn,
    setIdColumn,
    outIdColumn,
    setOutIdColumn,
    uuidVersion,
    setUuidVersion,
    sheetName,
    setSheetName,

    customPrefixMode,
    setCustomPrefixMode,
    customPrefixType,
    setCustomPrefixType,
    customPrefixLength,
    setCustomPrefixLength,
    customFixedPrefix,
    setCustomFixedPrefix,
    customConnector,
    setCustomConnector,
    customSuffixType,
    setCustomSuffixType,
    customSuffixLength,
    setCustomSuffixLength,
}) {
    const projectCodes = [
        "NRGI",
        "C4RE",
        "GSCD",
        "GEPM",
        "LDPP",
        "EPCC",
        "INFA",
        "MOSA",
        "CS4C",
        "PHNN",
        "PGEM",
        "G4PR",
    ];
    const patientEnabledProject = ["NRGI", "INFA"];
    const hasSelectedProject = project_code !="";
    const showCphiEntityType = strategy === "CPHI" && patientEnabledProject.includes(project_code); /*This is so that we show the entity types for the CPHI project as well */
    const showPcglEntityType = strategy === "PCGL" && patientEnabledProject.includes(project_code) ;
    const showPcglVariants = strategy === "PCGL" && hasSelectedProject;

    const pcglVariantOptionsByEntityType = {
        patient: ["SPE"],
        sample: ["EXP", "LIB", "RG", "WRK", "ANA"],
    };

    const selectedEntityType = entity_type || "sample";

    const availablePcglVariants =
    pcglVariantOptionsByEntityType[selectedEntityType] || [];

    const isPcglValidateMode = strategy === "PCGL" && mode === "validate";
    const isPcglGenerateMode = strategy === "PCGL" && mode === "generate";

    function togglePcglVariant(selectedVariant) {
    if (variants.includes(selectedVariant)) {
        setVariants(variants.filter((currentVariant) => currentVariant !== selectedVariant));
        return;
    }

    setVariants([...variants, selectedVariant]);
    }

    function getStrategyDescription(){
        if(strategy === "UUID"){
        return "Universally unique identifer. 128 bit number for identifying objects or information int he form of a 36 character alphanumerical string. "
        }
        if(strategy === "CPHI"){
        return "CPHI identifier specifications that follow the following structure: XXXX-000000. XXXX: A four character string identifying the project. 000000: six digit ID not encoding any metdata. \n All IDs processed with this strategy will be treated as sample IDs"
        }
        if(strategy === "PCGL"){
            return "PCGL identifier specification that is ready for submission into the PCGL. They should follow the structure of CPHI Identifiers of: XXXX-000000. XXXX: A four character string identifying the project. 000000: six digit ID not encoding any metdata. They can also include variants that depend on the entity type."
        }
        if(strategy === "CUSTOM"){
            return "Create/Validate a custom formatted ID. Please select the prefix rules, connector, and suffix rules."
        }
        return "Choose a identifier strategy to see its description"
    }
    return (
        <section className="config-panel">
            <div className="config-grid">
            {/*Mode */}
            <div className="config-card">
                <h3>Mode</h3>
                <div className="mode-button-group">
                <button
                    type="button"
                    className={mode === "validate"? "mode-button active" : "mode-button"}
                    onClick={() => setMode("validate")}
                >
                    <strong>Validate</strong>
                    <span>Check IDs and report invalid rows.</span>
                </button>

                <button
                    type="button"
                    className={mode === "generate"? "mode-button active" : "mode-button"}
                    onClick={() => setMode("generate")}
                >
                    <strong>Generate</strong>
                    <span>Generate IDs for missing rows. Will validate rows with exisitng IDs.</span>
                </button>
                </div>
            </div>

            {/*Identifier Strategy */}
            <div className="config-card">
                <h3>Identifier Strategy and Project</h3>
                <label>
                    Strategy
                    <select
                        value={strategy}
                        onChange={(e) => {
                            const selectedStrategy = e.target.value;

                            setStrategy(selectedStrategy);
                            setProjectId("");
                            setVariant("");
                            setVariants([]);

                            if (selectedStrategy === "CPHI" || selectedStrategy === "PCGL") {
                            setEntity_type("sample");
                            }
                        }}
                    >
                        <option value="UUID">UUID</option>
                        <option value="CPHI">CPHI</option>
                        <option value="PCGL">PCGL</option>
                        <option value="CUSTOM">Custom</option>
                    </select>
                </label>
                <div className="strategy-description">
                <strong>Description:</strong>
                <p>{getStrategyDescription()}</p>
                </div>

                <label>
                    <span className="label-with-tooltip">
                        Project Tag
                        <span className="tooltip">
                            ?
                            <span className="tooltip-text">
                                Select the database project used when checking for
                                existing identifiers. Matches inside the selected
                                project are conflicts. Matches in other projects
                                using the same strategy are warnings.
                            </span>
                        </span>
                    </span>

                    <select
                        value={projectId}
                        onChange={(e) => setProjectId(e.target.value)}
                        disabled={projectsLoading}
                    >
                        <option value="">
                            {projectsLoading
                                ? "Loading Project Tags..."
                                : "No Project Tag"}
                        </option>

                        {projects.map((project) => (
                            <option
                                key={project.id}
                                value={project.id}
                            >
                                {project.name}
                            </option>
                        ))}
                    </select>
                </label>
                <p className="field-help">
                    No Project Tag checks for conflicts across the complete strategy.
                </p>


            </div>

            {/*Configuration card */}
            <div className="config-card">
                <h3>Configuration</h3>

                {strategy == "UUID" && (
                <label>
                    UUID Version
                    <select value={uuidVersion} onChange={(e) => setUuidVersion(e.target.value)}>
                    <option value="4">Version 4</option>
                    <option value="7">Version 7</option>
                    </select>
                </label>
                )}

                {strategy == "CPHI" && (
                <>
                        
                    <label>
                        <span className="label-with-tooltip">
                            Project Code
                            <span className="tooltip">
                                ?
                                <span className="tooltip-text">
                                    The four character project prefix used at the start of the CPHI Identifiers regardless of patient or sample type. Some projects only work with sample IDs so please select carefully.
                                </span>
                            </span>
                        </span>
                        
                        {/*These are the list of available project codes. 
                        If new projects are added, add them as an option here */}
                        <select value={project_code} 
                                    onChange={(e) => {
                                        setProject_code(e.target.value)
                                        setEntity_type("sample"); 
                                    }}
                                >
                            <option value="">Select a Project Code</option>
                            {projectCodes.map((projectCode) => (
                                <option key={projectCode} value={projectCode}>
                                    {projectCode}
                                </option>
                            ))}
                        </select>
                    </label>

                    {showCphiEntityType && (
                        <label>
                            <span className="label-with-tooltip">
                                CPHI Entity Type
                                <span className="tooltip">
                                    ?
                                    <span className="tooltip-text">
                                        Choose whether the CPHI identifier belongs to a patient or sample. 
                                    </span>
                                </span>
                            </span>

                            <select value={entity_type} 
                                onChange={(e) => {
                                    setEntity_type(e.target.value); 
                                }}
                            >
                                <option value="sample">Sample</option>
                                <option value="patient">Patient</option>
                                
                            </select>
                        </label>
                    )}
                </>
                )}
                {strategy === "PCGL" &&(
                    <>
                        <label>
                            <span className="label-with-tooltip">
                                Project Code
                                <span className="tooltip">
                                    ?
                                    <span className="tooltip-text">
                                        The four character project prefix used at the start of the PCGL Identifiers regardless of patient or sample type. Some projects only work with sample IDs so please select carefully. Depending on selection, variants may be available as well.
                                    </span>
                                </span>
                            </span>
                            
                            {/*These are the list of available project codes. 
                            If new projects are added, add them as an option here */}
                            <select 
                                value={project_code} 
                                onChange={(e) => {
                                setProject_code(e.target.value);
                                setEntity_type("sample");
                                setVariant("");
                                setVariants([]);
                                }}
                            >
                                <option value="">Select a Project Code</option>
                                {projectCodes.map((projectCode) => (
                                    <option key={projectCode} value={projectCode}>
                                        {projectCode}
                                    </option>
                                ))}
                            </select>
                        </label>
                        {showPcglEntityType &&(
                            <label>
                                <span className="label-with-tooltip">
                                    PCGL Entity Type
                                    <span className="tooltip">
                                        ?
                                        <span className="tooltip-text">
                                            Choose whether the PCGL identifier belongs to a patient or sample. This decides what variants are available.
                                        </span>
                                    </span>
                                </span>

                                <select value={entity_type} 
                                    onChange={(e) => {
                                        setEntity_type(e.target.value); 
                                        setVariant("");
                                        setVariants([]);
                                    }}
                                >
                                    <option value="sample">Sample</option>
                                    <option value="patient">Patient</option>
                                    
                                </select>
                            </label>
                        )}
                        {showPcglVariants && isPcglValidateMode && (
                            <label>
                                <span className="label-with-tooltip">
                                Variant
                                <span className="tooltip">
                                    ?
                                    <span className="tooltip-text">
                                    Optional PCGL variant to validate. Leave as None to validate base PCGL IDs.
                                    </span>
                                </span>
                                </span>

                                <select value={variant} onChange={(e) => setVariant(e.target.value)}>
                                <option value="">None</option>

                                {availablePcglVariants.map((variantOption) => (
                                    <option key={variantOption} value={variantOption}>
                                    {variantOption}
                                    </option>
                                ))}
                                </select>
                            </label>
                            )}

                            {showPcglVariants && isPcglGenerateMode && (
                            <div className="checkbox-field">
                                <span className="label-with-tooltip">
                                Variants to Generate
                                <span className="tooltip">
                                    ?
                                    <span className="tooltip-text">
                                    Select one or more PCGL variants. The uploaded file must already contain valid base PCGL IDs.
                                    </span>
                                </span>
                                </span>

                                <div className="checkbox-group">
                                {availablePcglVariants.map((variantOption) => (
                                    <label key={variantOption} className="checkbox-option">
                                    <input
                                        type="checkbox"
                                        checked={variants.includes(variantOption)}
                                        onChange={() => togglePcglVariant(variantOption)}
                                    />
                                    <span>{variantOption}</span>
                                    </label>
                                ))}
                                </div>

                                <p className="field-help">
                                If no variant is selected, PCGL generation will use base ID generation.
                                </p>
                            </div>
                        )}
                    </>
                    
                )}
                {strategy === "CUSTOM" &&(
                    <>
                        <label>
                            <span className="label-with-tooltip">
                                Prefix Mode
                                <span className="tooltip">
                                    ?
                                    <span className="tooltip-text">
                                        Choose between a fixed prefix for all identifiers and random prefixes that follow your indicated format.
                                    </span>
                                </span>
                            </span>

                            <select value={customPrefixMode} 
                                onChange={(e) => {
                                    setCustomPrefixMode(e.target.value); 
                                }}
                            >
                                <option value="random">Random</option>
                                <option value="fixed">Fixed</option>
                            </select>
                        </label>

                        {customPrefixMode === "fixed" &&(
                            <label>
                                <span className="label-with-tooltip">
                                    Fixed Prefix
                                    <span className="tooltip">
                                        ?
                                        <span className="tooltip-text">
                                            Please input the fixed prefix you would like all your IDs to have
                                        </span>
                                    </span>
                                </span>

                                <input
                                    type="text"
                                    value={customFixedPrefix}
                                    onChange={(e)=> setCustomFixedPrefix(e.target.value)}
                                    placeholder="Example: C3G"
                                />
                            </label>
                        )}
                        {customPrefixMode === "random" && (
                            <>
                                <label>
                                    <span className="label-with-tooltip">
                                        Prefix Type
                                        <span className="tooltip">
                                            ?
                                            <span className="tooltip-text">
                                                Choose whether the random prefix should contain letters, numbers, or both.
                                            </span>
                                        </span>
                                    </span>

                                    <select
                                        value={customPrefixType}
                                        onChange={(e) => setCustomPrefixType(e.target.value)}
                                    >
                                        <option value="letters">Letters</option>
                                        <option value="numeric">Numeric</option>
                                        <option value="alphanumeric">Alphanumeric</option>
                                    </select>
                                </label>

                                <label>
                                    <span className="label-with-tooltip">
                                        Prefix Length
                                        <span className="tooltip">
                                            ?
                                            <span className="tooltip-text">
                                                Choose how many characters the random prefix should have.
                                            </span>
                                        </span>
                                    </span>

                                    <input
                                        type="number"
                                        min="1"
                                        value={customPrefixLength}
                                        onChange={(e) => setCustomPrefixLength(e.target.value)}
                                    />
                                </label>
                            </>
                        )}
                        <label>
                            <span className="label-with-tooltip">
                                Connector
                                <span className="tooltip">
                                ?
                                <span className="tooltip-text">
                                    Choose what separates the prefix and suffix.
                                </span>
                                </span>
                            </span>

                            <select
                                value={customConnector}
                                onChange={(e) => setCustomConnector(e.target.value)}
                            >
                                <option value="-">Dash (-)</option>
                                <option value="_">Underscore (_)</option>
                                <option value="+">Plus (+)</option>
                                <option value="">None</option>
                            </select>
                        </label>

                        <label>
                            <span className="label-with-tooltip">
                                Suffix Type
                                <span className="tooltip">
                                    ?
                                    <span className="tooltip-text">
                                        Choose whether the suffix should contain letters, numbers, or both.
                                    </span>
                                </span>
                            </span>
                            <select 
                                value = {customSuffixType}
                                onChange = {(e)=> setCustomSuffixType(e.target.value)}
                            >
                                <option value="letters">Letters</option>
                                <option value="numeric">Numeric</option>
                                <option value="alphanumeric">Alphanumeric</option>
                            </select>
                        </label>

                        <label>
                            <span className="label-with-tooltip">
                                Suffix Length
                                <span className="tooltip">
                                    ?
                                    <span className="tooltip-text">
                                        Select the length your suffix should have in number of characters.
                                    </span>
                                </span>
                            </span>
                            <input
                                type="number"
                                min="1"
                                value = {customSuffixLength}
                                onChange={(e)=> setCustomSuffixLength(e.target.value)}
                            />
                        </label>
                    </>    
                )}

                
            </div>

            {/*Input/Output Card */}
            <div className="config-card">
                <h3>Input/Output</h3>
                <label>
                    <span className="label-with-tooltip">
                        Input ID Column Name:
                        <span className="tooltip">
                            ?
                            <span className="tooltip-text">
                                Input ID column name refers to the name of the header of your ID column. Common names include identifier, ID Name, ID.
                            </span>
                        </span>
                    </span>
                <input type="text" value={idColumn} onChange={(e) => setIdColumn(e.target.value)} placeholder="identifier" />

                </label>
                <label>
                    <span className="label-with-tooltip">
                        Output ID Column Name:
                        <span className="tooltip">
                            ?
                            <span className="tooltip-text">
                                The name of the ID column in the output file. Leave empty to use the input ID column name.
                            </span>
                        </span>
                    </span>
                <input type="text" value={outIdColumn} onChange={(e) => setOutIdColumn(e.target.value)} placeholder={idColumn||"identifier"}/>
                </label>
                {/*<p className="output-field-help">Leave output field empty to use the input ID column name.</p>*/}
                <label>
                    <span className="label-with-tooltip">
                        Excel Sheet Name:
                        <span className="tooltip">
                            ?
                            <span className="tooltip-text">
                                Optional value. Choose the excel sheet within your file to validate/generate. Leaving it empty will use the active sheet.
                            </span>
                        </span>
                    </span>
                    <input
                        type="text"
                        value={sheetName}
                        onChange={(e) => setSheetName(e.target.value)}
                        placeholder="Optional, example: UserSampleSubmission"
                    />
                </label>
            </div>

            
            </div>
        </section>
    )
}
export default ConfigPanel;