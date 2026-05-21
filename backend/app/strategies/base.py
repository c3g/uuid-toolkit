import abc


class StrategyInterface(abc.ABC):

    @abc.abstractmethod
    def validate(self, identifier: str, config: dict | None = None) -> dict:
        """
        Validate the given identifier.

        Returns:
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
        """
        pass