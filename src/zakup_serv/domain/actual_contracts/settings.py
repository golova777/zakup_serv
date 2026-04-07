from dataclasses import dataclass
from enum import Enum

class BaseQueryParams:
    query_param = None
    value = None


# Параметры запроса реестра контрактов ЕИС
class EISContractsQueryParams(Enum):
    CUSTOMER_REGION = 'customerPlace'
    CONTRACT_DATE_FROM = 'contractDateFrom'
    CONTRACT_DATE_TO = 'contractDateTo'
    CONTRACT_PRICE_FROM = 'contractPriceFrom'
    CONTRACT_PRICE_TO = 'contractPriceTo'


# Регионы поиска
@dataclass
class CustomerRegions:
    query_param = EISContractsQueryParams.CUSTOMER_REGION
    regions = [
        {"Kostroma region": "44000000000",},
    ]


# Начальный диапазон цены поиска
class MinContractPrice:
    query_param = EISContractsQueryParams.CONTRACT_PRICE_FROM
    value = 0

class MaxContractPrice:
    query_param = EISContractsQueryParams.CONTRACT_PRICE_TO
    value = 100000000000

