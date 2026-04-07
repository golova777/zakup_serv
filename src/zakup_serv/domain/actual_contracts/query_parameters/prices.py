from zakup_serv.infrastructure.adapters import QueryParamAdapter
from zakup_serv.settings import EISContractsQueryParams


class MinPrice:
    def __init__(self, min_price: int):
        self.min_price = min_price
        self.query_param = QueryParamAdapter(
            param_name=EISContractsQueryParams.CONTRACT_PRICE_FROM.value,
            param_value=str(self.min_price)
        )

    def __repr__(self):
        return f"{self.__class__.__name__}(min_price={self.min_price}, query_param_name={self.query_param.param_name})"


class MaxPrice:
    def __init__(self, max_price: int):
        self.max_price = max_price
        self.query_param = QueryParamAdapter(
            param_name=EISContractsQueryParams.CONTRACT_PRICE_TO.value,
            param_value=str(self.max_price)
        )

    def __repr__(self):
        return f"{self.__class__.__name__}(max_price={self.min_price}, query_param_name={self.query_param.param_name})"
