# from zakup_serv.domain.marketplaces.zakupki_gov_ru.contracts.contract_config import MARKETPLACE_INFO
# from zakup_serv.domain.marketplaces.zakupki_gov_ru.contracts.query_parameters.base import QueryParam
# from zakup_serv.infrastructure.adapters import QueryParamAdapter
#
# query_params = MARKETPLACE_INFO["44FZ"]["query_params"]
#
#
# class ReestrNumber(QueryParam):
#     # параметр номера контракта в реестре контрактов
#
#     def __init__(self, contract_number: str):
#         super().__init__()
#         self.contract_number = contract_number
#         self.query_param = QueryParamAdapter(
#             param_name=query_params.CONTRACT_REESTR_NUM.value,
#             param_value=str(self.contract_number),
#         )
#
#     def __repr__(self):
#         return (f"{self.__class__.__name__}(reestr_number={self.contract_number}, "
#                 f"query_param_name={self.query_param.param_name})")
#
