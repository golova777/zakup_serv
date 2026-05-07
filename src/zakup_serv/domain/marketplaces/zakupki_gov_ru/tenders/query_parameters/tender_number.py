# from zakup_serv.domain.marketplaces.zakupki_gov_ru.contracts.contract_config import MARKETPLACE_INFO
# from zakup_serv.domain.marketplaces.zakupki_gov_ru.contracts.query_parameters.base import QueryParam
from zakup_serv.domain.marketplaces.zakupki_gov_ru.tenders.query_parameters.base import QueryParam
from zakup_serv.domain.marketplaces.zakupki_gov_ru.tenders.tender_config import TENDER_MARKETPLACE_INFO
from zakup_serv.infrastructure.adapters import QueryParamAdapter

query_params = TENDER_MARKETPLACE_INFO["EIS"]["query_params"]



class TenderNumber(QueryParam):
    # параметр номера контракта в реестре контрактов

    def __init__(self, tender_number: str):
        super().__init__()
        self.tender_number = tender_number
        self.query_param = QueryParamAdapter(
            param_name=query_params.TENDER_REG_NUMBER.value,
            param_value=str(self.tender_number),
        )

    def __repr__(self):
        return (f"{self.__class__.__name__}(reestr_number={self.tender_number}, "
                f"query_param_name={self.query_param.param_name})")

