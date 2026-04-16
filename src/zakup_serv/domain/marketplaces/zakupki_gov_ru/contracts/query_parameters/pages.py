from zakup_serv.domain.marketplaces.zakupki_gov_ru.config import MARKETPLACE_INFO
from zakup_serv.infrastructure.adapters import QueryParamAdapter

query_params = MARKETPLACE_INFO["44FZ"]["query_params"]


class Page:
    # параметр номера страницы

    def __init__(self, page_num: int):
        self.page_num = page_num
        self.query_param = QueryParamAdapter(
            param_name=query_params.PAGE.value,
            param_value=str(self.page_num),
        )


class PerPage:
    #  параметр записей на страницу списка контрактов ( _число )

    def __init__(self, per_page_entries: int):
        self.per_page_entries = per_page_entries
        self.query_param = QueryParamAdapter(
            param_name=query_params.PER_PAGE.value,
            param_value="_" + str(self.per_page_entries),
        )
