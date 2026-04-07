from dataclasses import dataclass
from pathlib import Path
from enum import Enum


# Регионы поиска
contract_search_regions = {
    "Kostroma region": "44000000000",
}





# Начальный диапазон цены поиска
search_min_max_price = (0, 100000000000)

class EISContractsQueryParams(Enum):
    CUSTOMER_REGION = 'customerPlace'
    CONTRACT_DATE_FROM = 'contractDateFrom'
    CONTRACT_DATE_TO = 'contractDateTo'
    CONTRACT_PRICE_FROM = 'contractPriceFrom'
    CONTRACT_PRICE_TO = 'contractPriceTo'



