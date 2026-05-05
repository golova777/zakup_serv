import os
from dotenv import load_dotenv
from enum import Enum

load_dotenv()


class QueryParams(Enum):
    CUSTOMER_REGION = "customerPlace"
    CONTRACT_DATE_FROM = "contractDateFrom"
    CONTRACT_DATE_TO = "contractDateTo"
    CONTRACT_PRICE_FROM = "contractPriceFrom"
    CONTRACT_PRICE_TO = "contractPriceTo"
    PAGE = "pageNumber"
    PER_PAGE = "recordsPerPage"
    CONTRACT_REESTR_NUM = "reestrNumber"


MARKETPLACE_INFO = {
    "44FZ": {
        "base_url": "https://zakupki.gov.ru/epz/contract/search/results.html?morphology=on&"
        "fz44=on&contractStageList_0=on&contractStageList_1=on&contractStageList_2=on&"
        "contractStageList_3=on&contractStageList=0%2C1%2C2%2C3&selectedContractDataChanges=ANY&"
        "contractPriceFrom=0&contractPriceTo=100000000000&budgetLevelsIdNameHidden=%7B%7D&"
        "customerPlace=44000000000&"
        "contractDateFrom=01.01.2025&contractDateTo=31.03.2025&countryRegIdNameHidden=%7B%7D&"
        "sortBy=UPDATE_DATE&"
        "pageNumber=1&sortDirection=false&recordsPerPage=_10&"
        "showLotsInfoHidden=false",
        "regions": {
            # "44000000000": "Костромская область",
        },
        "fallback_dates": {
            "from": "01.01.2026",
            "to": "30.02.2026",
        },
        "price": (1, 100000000000),
        "max_span_contracts": 3000, # для разбивки диапазонов цен
        "db_limit_max_span_contracts": 5000, # для определения количества страниц с контрактами
        "default_per_page_items": 10,
        "default_page_num": 1,
        "default_proxy": None,
        "query_params": QueryParams,
        "dwl_stages": {
            "price_spans": "1_price_spans",
            "contracts_pages": "2_conatract_lists_pages",
            "contracts_data": "3_contracts_data",
        },
        "contracts_file_processed_mark": "processed_",
        "default_fetch_contracts_concurency": 1,
    },
    "223FZ": {},
}


"""
RETRIABLE_HTTP_STATUS_CODES = [429, 500, 502, 503, 504]


DEFAULT_RETRY_POLICY = {
    "retries": 3,
    "backoff_factor": 0.5,
    "delay_increase_func": lambda b, c: b * (c**2),
    "status_forcelist": RETRIABLE_HTTP_STATUS_CODES,
    "skip_not_retriable": False,
}





DEFAULT_TARGET_URLS = {
    "CONTRACTS_44_FZ": "https://zakupki.gov.ru/epz/contract/search/results.html?"
    "morphology=on&fz44=on&contractStageList_0=on&contractStageList=0&"
    "selectedContractDataChanges=ANY&contractPriceFrom=1000&"
    "contractPriceTo=500000&budgetLevelsIdNameHidden=%7B%7D&"
    "customerPlace=44000000000&contractDateFrom=01.01.2026&"
    "contractDateTo=30.03.2026&countryRegIdNameHidden=%7B%7D&"
    "sortBy=UPDATE_DATE&pageNumber=1&sortDirection=false&"
    "recordsPerPage=_10&showLotsInfoHidden=false",
}


DEFAULTS = {
    "PROXY": os.getenv("TEXT_PROXY", None),
    "CONCURRENT_CONNECTIONS": 10,
    "FETCH_PAGE_TIMEOUT": 2000,
    "HTTP_METHOD": "GET",
    "CHECK_SSL": False,
    "HEADERS": {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/145.0.0.0 Safari/537.36"
    },
}

SAVERS_DEFAULTS = {
    "SAVE_FOLDER": "./saves/",
    "FILE_NAME_PREFIX": "data",
    "FILE_EXTENSION": "txt",
}


# Регионы поиска
contract_search_regions = {
    "Костромская область": "44000000000",
    # "Yaroslavl region": "76000000000",
    # "Vladimir region": "33000000000",
    # "Ivanovo region": "37000000000",
}

# Начальный диапазон цены поиска
search_min_max_price = (0, 100000000000)


class EISContractsQueryParams(Enum):
    CUSTOMER_REGION = "customerPlace"
    CONTRACT_DATE_FROM = "contractDateFrom"
    CONTRACT_DATE_TO = "contractDateTo"
    CONTRACT_PRICE_FROM = "contractPriceFrom"
    CONTRACT_PRICE_TO = "contractPriceTo"
    PAGE = "pageNumber"
    PER_PAGE = "recordsPerPage"
    
    
"""
