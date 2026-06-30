"""
Shared strategy interface for identifier validation and generation.

This module defines the abstract interface that every identifier strategy must
implement. By forcing all strategies to provide the same validate() and
generate() methods, the pipeline can work with UUID, CPHI, CUSTOM, and future
strategies without needing strategy-specific logic.

Each concrete strategy must implement:
- validate(identifier, config): validates an existing identifier.
- generate(config): generates a new identifier using strategy-specific rules.

This module uses Python's abc library to define an abstract base class.
Concrete strategy classes should inherit from StrategyInterface and implement
all abstract methods.
"""
import abc


class StrategyInterface(abc.ABC):
    """
    Abstract base class for all identifier strategies.

    Every strategy must implement validate() and generate() so the pipeline can
    call the same methods regardless of which strategy is selected.

    The validate() method must return a consistent dictionary shape across all
    strategies. The generate() method must return a newly generated identifier
    string based on the selected strategy and config.
    """

    @abc.abstractmethod
    def validate(self, identifier: str, config: dict | None = None) -> dict:
        """
        Validate existing identifier

        Parameters
        ----------
        identifier:
            Identifier string to validate
        config:
            A dict containing varying values depending on the concrete strategy involved.
            For example, CPHI may require project codes or the variant to validate against.
        Validate the given identifier.

        Returns
        -------
            {
                "valid": bool,
                "error": str | None,
                "message": str
            }
        """
        pass

    @abc.abstractmethod
    def generate(self, config: dict | None = None) -> str:
        """
        Generate a new identifier according to the strategy's rules.

        Parameters
        ----------
        config:
            A dict containing varying values depending on the concrete strategy involved.
            The values in the config help dictate how to generate the identifier and where to place values.
            For example CPHI would require the project code and also the variant in order to place the project code in the front and whether to concatenate a variant.
        """
        pass

    def get_strategy_info(self, config:dict | None = None) -> dict:
        """
        Returns strategy metadata that tells the pipeline how this strategy behaves in terms of validation and generation.

        Default Behaviour:
        - Generate missing identifiers
        - Validate existing identifiers and leave them unchanged
        - Write one generated identifier into one output column

        """
        return {
            "generation_mode":"fill_missing",
            "output_mode":"single_column",
            "requires_existing_identifier": False,
            "preserve_input_identifier":False,
        }
    def generate_derived_identifiers(
        self,
        source_identifier: str,
        config: dict | None = None,
    ) -> dict[str, str]:
        """
        Generate one or more identifiers from an existing source identifier.

        Strategies that support derived generation should override this method.

        Example:
            source_identifier = "NRGI-123456"

            returns:
            {
                "pcgl_EXP_id": "NRGI-123456_EXP_4829",
                "pcgl_LIB_id": "NRGI-123456_LIB_1038"
            }
        """
        raise NotImplementedError(
            "This strategy does not support derived identifier generation."
        )