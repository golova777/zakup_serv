from zakup_serv.domain.marketplaces.zakupki_gov_ru.config import MARKETPLACE_INFO
from zakup_serv.infrastructure.adapters import QueryParamAdapter

query_params = MARKETPLACE_INFO["44FZ"]["query_params"]


class StartDate:
    def __init__(self, start_date):
        self.start_date = start_date
        self.query_param = QueryParamAdapter(
            param_name=query_params.CONTRACT_DATE_FROM.value,
            param_value=self.start_date,
        )

    def __repr__(self):
        return f"{self.__class__.__name__}(start_date={self.start_date}, param_name={self.query_param.param_name})"


class EndDate:
    def __init__(self, end_date):
        self.end_date = end_date
        self.query_param = QueryParamAdapter(
            param_name=query_params.CONTRACT_DATE_TO.value,
            param_value=self.end_date,
        )

    def __repr__(self):
        return f"{self.__class__.__name__}(end_date={self.end_date}, param_name={self.query_param.param_name})"
