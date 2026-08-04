"""
Shared interface for all identifier strategies.

The validation and generation pipelines use this interface so they can work
with UUID, CPHI, PCGL, CUSTOM, and future strategies without needing separate
pipeline logic for every format.

How this file connects to the rest of the project
--------------------------------------------------
- ``registry.py`` selects and returns a concrete strategy.
- Concrete strategy classes inherit from ``StrategyInterface``.
- The pipelines call the methods defined here.
- File-level duplicates and database conflicts are handled by the pipelines,
  not by the individual strategy classes.
- ``ConfigPanel.jsx`` collects strategy-specific user options.
- ``ToolkitPage.jsx`` builds the config sent to the backend.

Adding a new strategy
---------------------
Backend:
1. Create a new strategy class that inherits ``StrategyInterface``.
2. Implement ``validate()`` and ``generate()``.
3. Register the strategy in ``registry.py``.
4. Add config validation in the API/config validation layer if needed.
5. Add unit and pipeline tests.

Frontend:
1. Add the strategy to the strategy selector in ``ConfigPanel.jsx``.
2. Add any strategy-specific controls.
3. Update ``ToolkitPage.jsx`` so ``buildConfig()`` sends the required values.

This file normally does not need to change when a new strategy is added unless
the new strategy requires a pipeline behavior that the current interface
cannot represent.
"""

import abc


class StrategyInterface(abc.ABC):
    """
    Define the methods and optional hooks shared by all identifier strategies.

    A normal strategy only needs to implement ``validate()`` and ``generate()``.
    Strategies that generate several identifiers from one existing identifier
    can also override ``get_strategy_info()`` and
    ``generate_derived_identifiers()``.
    """

    @abc.abstractmethod
    def validate(
        self,
        identifier: str,
        config: dict | None = None,
    ) -> dict:
        """
        Validate one identifier using the strategy's rules.

        Parameters
        ----------
        identifier:
            Identifier value to validate.

        config:
            Optional strategy configuration. The required keys depend on the
            concrete strategy. For example, UUID uses ``version`` while CPHI
            and PCGL may use ``project_code`` and ``entity_type``.

        Returns
        -------
        dict
            A validation result with the shared shape:

            {
                "valid": bool,
                "error": str | None,
                "message": str,
            }

            ``valid`` states whether the identifier passed validation.
            ``error`` contains a short error category or ``None``.
            ``message`` contains the explanation shown to the user.

        Notes
        -----
        This method handles format and strategy-specific checks only.
        Duplicate checks and database comparisons are handled later by the
        pipelines.
        """
        pass

    @abc.abstractmethod
    def generate(
        self,
        config: dict | None = None,
    ) -> str:
        """
        Generate one identifier using the strategy's rules.

        Parameters
        ----------
        config:
            Optional strategy configuration. Required values depend on the
            concrete strategy.

        Returns
        -------
        str
            A newly generated identifier.

        Raises
        ------
        ValueError
            Raised when required config values are missing or invalid.

        Notes
        -----
        This method only creates a candidate identifier. The generation
        pipeline checks it against identifiers from the file, other generated
        identifiers, and the database.
        """
        pass

    def get_strategy_info(
        self,
        config: dict | None = None,
    ) -> dict:
        """
        Return metadata that tells the generation pipeline how to run.

        Parameters
        ----------
        config:
            Optional strategy configuration. A strategy may inspect the config
            when its generation behavior changes based on selected options.

        Returns
        -------
        dict
            Metadata describing the generation workflow:

            ``generation_mode``
                ``"fill_missing"`` means identifiers are generated for rows
                where the input identifier is missing.

            ``output_mode``
                ``"single_column"`` means one generated identifier is written
                for each row.

            ``requires_existing_identifier``
                States whether generation needs an existing source identifier.

            ``preserve_input_identifier``
                States whether the original identifier should remain in the
                output when derived identifiers are generated.

        Notes
        -----
        Most strategies should use this default behavior. Override this method
        when a strategy uses derived generation or multiple output columns.
        """
        return {
            "generation_mode": "fill_missing",
            "output_mode": "single_column",
            "requires_existing_identifier": False,
            "preserve_input_identifier": False,
        }

    def generate_derived_identifiers(
        self,
        source_identifier: str,
        config: dict | None = None,
    ) -> dict[str, str]:
        """
        Generate several identifiers from one existing source identifier.

        Strategies that support derived generation should override this method.

        Parameters
        ----------
        source_identifier:
            Existing identifier used as the base for the generated identifiers.

        config:
            Optional strategy configuration, including any selected variants
            or derived identifier types.

        Returns
        -------
        dict[str, str]
            A mapping from a variant or output label to its generated value.

            Example:

            {
                "EXP": "NRGI-123456_EXP_4829",
                "LIB": "NRGI-123456_LIB_1038",
            }

        Raises
        ------
        NotImplementedError
            Raised when the strategy does not support derived generation.

        Notes
        -----
        A strategy that overrides this method should normally also override
        ``get_strategy_info()`` so the pipeline uses the derived-generation
        workflow.
        """
        raise NotImplementedError(
            "This strategy does not support derived identifier generation."
        )