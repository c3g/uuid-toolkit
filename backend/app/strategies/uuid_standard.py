import uuid
from .base import StrategyInterface

class UUIDStrategy(StrategyInterface):
    _GENERATORS = {
        4: uuid.uuid4,
        #7: uuid.uuid7, #right now testing for python version that arent 3.14+
    }


    #validating to see if the uuid is a valid uuid and it matches the version the user indicated
    def validate(self, identifier: str, config :dict | None = None) -> dict:
        
        
        if identifier is None:
            return {
                "valid" : False,
                "error": "Missing identifier",
                "message": "Identifier not present."
            }
        if not isinstance(identifier, str):
            return {
                "valid" : False,
                "error": "Invalid type",
                "message": f"Expected a string identifier, but got {type(identifier).__name__}."
            }
        
        if config is None or "version" not in config:
            return {
                "valid" : False,
                "error": "Missing config or version for UUID validation",
                "message": "Missing config or version for UUID validation. 'version' is required in config."
            }
        expected_version = config["version"]

        try:
            parsed = uuid.UUID(identifier)
        except ValueError:
            return {
                "valid" : False,
                "error": "Invalid UUID format",
                "message": f"Identifier '{identifier}' is not a valid UUID string."
            }
        if parsed.version != expected_version:
            return {
                "valid" : False,
                "error": "UUID version mismatch",
                "message": f"Expected UUID version {expected_version}, but got version {parsed.version}."
            }
        return {
            "valid" : True,
            "error": None,
            "message": f"Identifier is a valid UUID version {expected_version}."
        }

        #MISSING: have to check the identifier against database to ensure it is unique, 
        

    def generate(self, config: dict | None = None) -> str:
        if config is None:
            raise ValueError("Missing config for UUID generation. 'version' is required.")
        if "version" not in config:
            raise ValueError("Missing 'version' in config for UUID strategy.")
        if config["version"] is None:
            raise ValueError("UUID version cannot be None.")
        version = config["version"]
        try:
            generator = self._GENERATORS[version]
        except KeyError:
            raise ValueError(f"Unsupported UUID version: {version}")
        return str(generator())

        #MISSING: have to check the generated uuid against database to ensure uniquness
    


#print("UUIDStrategy defined:", "UUIDStrategy" in globals()). #TESTING function