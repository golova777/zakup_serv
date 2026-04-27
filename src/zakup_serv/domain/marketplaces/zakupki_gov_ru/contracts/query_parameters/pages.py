from zakup_serv.domain.marketplaces.zakupki_gov_ru.config import MARKETPLACE_INFO
from zakup_serv.domain.marketplaces.zakupki_gov_ru.contracts.query_parameters.base import QueryParam
from zakup_serv.infrastructure.adapters import QueryParamAdapter

query_params = MARKETPLACE_INFO["44FZ"]["query_params"]


class Page(QueryParam):
    # параметр номера страницы

    def __init__(self, page_num: int):
        super().__init__()
        self.page_num = page_num
        self.query_param = QueryParamAdapter(
            param_name=query_params.PAGE.value,
            param_value=str(self.page_num),
        )

    def __repr__(self):
        return f"{self.__class__.__name__}(page_num={self.page_num}, query_param_name={self.query_param.param_name})"


class PerPage(QueryParam):
    #  параметр записей на страницу списка контрактов ( _число )

    def __init__(self, per_page_entries: int):
        super().__init__()
        self.per_page_entries = per_page_entries
        self.query_param = QueryParamAdapter(
            param_name=query_params.PER_PAGE.value,
            param_value="_" + str(self.per_page_entries),
        )

    def __repr__(self):
        return f"{self.__class__.__name__}(per_page_entries={self.per_page_entries}, query_param_name={self.query_param.param_name})"

