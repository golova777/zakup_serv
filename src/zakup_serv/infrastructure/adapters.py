class QueryParamAdapter:
    """Adapter for query parameters in HTTP requests."""

    def __init__(self, param_name: str = "", param_value: str = ""):
        self.param_name = param_name
        self.param_value = param_value
