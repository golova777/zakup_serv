from zakup_serv.domain.marketplaces.zakupki_gov_ru.contracts.contract_config import MARKETPLACE_INFO
from zakup_serv.domain.marketplaces.zakupki_gov_ru.contracts.query_parameters.base import QueryParam
from zakup_serv.infrastructure.adapters import QueryParamAdapter

query_params = MARKETPLACE_INFO["44FZ"]["query_params"]


class MinPrice(QueryParam):
    def __init__(self, min_price: int):
        super().__init__()
        self.min_price = min_price
        self.query_param = QueryParamAdapter(
            param_name=query_params.CONTRACT_PRICE_FROM.value,
            param_value=str(self.min_price),
        )

    def __repr__(self):
        return f"{self.__class__.__name__}(min_price={self.min_price}, query_param_name={self.query_param.param_name})"


class MaxPrice(QueryParam):
    def __init__(self, max_price: int):
        super().__init__()
        self.max_price = max_price
        self.query_param = QueryParamAdapter(
            param_name=query_params.CONTRACT_PRICE_TO.value,
            param_value=str(self.max_price),
        )

    def __repr__(self):
        return f"{self.__class__.__name__}(max_price={self.max_price}, query_param_name={self.query_param.param_name})"
