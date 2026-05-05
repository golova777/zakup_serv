from zakup_serv.domain.marketplaces.zakupki_gov_ru.tenders.query_parameters.base import QueryParam
from zakup_serv.domain.marketplaces.zakupki_gov_ru.tenders.tender_config import TENDER_MARKETPLACE_INFO
from zakup_serv.infrastructure.adapters import QueryParamAdapter

query_params = TENDER_MARKETPLACE_INFO["EIS"]["query_params"]


class StartDate(QueryParam):
    def __init__(self, start_date):
        super().__init__()
        self.start_date = start_date
        self.query_param = QueryParamAdapter(
            param_name=query_params.PUBLISH_DATE_FROM.value,
            param_value=self.start_date,
        )

    def __repr__(self):
        return f"{self.__class__.__name__}(start_date={self.start_date}, param_name={self.query_param.param_name})"


class EndDate(QueryParam):
    def __init__(self, end_date):
        super().__init__()
        self.end_date = end_date
        self.query_param = QueryParamAdapter(
            param_name=query_params.PUBLISH_DATE_TO.value,
            param_value=self.end_date,
        )

    def __repr__(self):
        return f"{self.__class__.__name__}(end_date={self.end_date}, param_name={self.query_param.param_name})"
