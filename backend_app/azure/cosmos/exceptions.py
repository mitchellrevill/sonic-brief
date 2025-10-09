# Minimal stub for azure.cosmos.exceptions used by tests and linters.
# This file intentionally provides only the symbols referenced by the
# test suite and by other modules in this project. It's not a replacement for
# the real azure.cosmos.exceptions package when running against Azure.

class CosmosResourceNotFoundError(Exception):
    pass

class CosmosHttpResponseError(Exception):
    def __init__(self, message: str = "", status_code: int | None = None):
        super().__init__(message)
        self.status_code = status_code

# Generic alias used in some test imports
class CosmosError(Exception):
    pass
