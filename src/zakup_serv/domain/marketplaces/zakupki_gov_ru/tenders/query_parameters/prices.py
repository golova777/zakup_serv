from zakup_serv.domain.marketplaces.zakupki_gov_ru.tenders.query_parameters.base import QueryParam
from zakup_serv.domain.marketplaces.zakupki_gov_ru.tenders.tender_config import TENDER_MARKETPLACE_INFO
from zakup_serv.infrastructure.adapters import QueryParamAdapter

query_params = TENDER_MARKETPLACE_INFO["EIS"]["query_params"]

class TenderMinPrice(QueryParam):
    def __init__(self, min_price: int | None = None):
        super().__init__()
        self.min_price = min_price or 0
        self.query_param = QueryParamAdapter(
            param_name=query_params.PRICE_FROM.value,
            param_value=str(self.min_price),
        )

    def __repr__(self):
        return f"{self.__class__.__name__}(min_price={self.min_price}, query_param_name={self.query_param.param_name})"


class TenderMaxPrice(QueryParam):
    def __init__(self, max_price: int | None = None):
        super().__init__()
        self.max_price = max_price or 0
        self.query_param = QueryParamAdapter(
            param_name=query_params.PRICE_TO.value,
            param_value=str(self.max_price),
        )

    def __repr__(self):
        return f"{self.__class__.__name__}(max_price={self.max_price}, query_param_name={self.query_param.param_name})"
