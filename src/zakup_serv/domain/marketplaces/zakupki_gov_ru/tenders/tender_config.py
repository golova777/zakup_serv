from dotenv import load_dotenv
from enum import Enum

load_dotenv()


class TenderQueryParams(Enum):
    CUSTOMER_REGION = "customerPlace"
    PUBLISH_DATE_FROM = "publishDateFrom"
    PUBLISH_DATE_TO = "publishDateTo"
    PAGE = "pageNumber"
    SORT_DIRECTION = "sortDirection"
    PER_PAGE = "recordsPerPage"


TENDER_MARKETPLACE_INFO = {
    "EIS": {
        "query_params": TenderQueryParams,
        "SAVE_FOLDER": "./saves/tenders/",
        "dwl_stages": {
            "tenders_pages": "tenders_pages",
        },
        "base_url": "https://zakupki.gov.ru/epz/order/extendedsearch/results.html?"
                    "morphology=on&"
                    "search-filter=+%D0%94%D0%B0%D1%82%D0%B5+%D1%80%D0%B0%D0%B7%D0%BC%D0%B5%D1%89%D0%B5%D0%BD%D0%B8%D1%8F&"
                    "pageNumber=1&"
                    "sortDirection=false&"
                    "recordsPerPage=_10&"
                    "showLotsInfoHidden=false&"
                    "sortBy=PUBLISH_DATE&"
                    "fz44=on&"
                    "fz223=on&"
                    "ppRf615=on&"
                    "af=on&"
                    "currencyIdGeneral=-1&"
                    "publishDateFrom=05.05.2026&"
                    "customerPlace=77000000000&"
                    "customerPlaceCodes=77000000000&"
                    "gws=%D0%92%D1%8B%D0%B1%D0%B5%D1%80%D0%B8%D1%82%D0%B5+%D1%82%D0%B8%D0%BF+%D0%B7%D0%B0%D0%BA%D1%83%D0%BF%D0%BA%D0%B8",
        "default_page_num": 1,


        # "base_url": "https://zakupki.gov.ru/epz/contract/search/results.html?morphology=on&"
        # "fz44=on&contractStageList_0=on&contractStageList_1=on&contractStageList_2=on&"
        # "contractStageList_3=on&contractStageList=0%2C1%2C2%2C3&selectedContractDataChanges=ANY&"
        # "contractPriceFrom=0&contractPriceTo=100000000000&budgetLevelsIdNameHidden=%7B%7D&"
        # "customerPlace=44000000000&"
        # "contractDateFrom=01.01.2025&contractDateTo=31.03.2025&countryRegIdNameHidden=%7B%7D&"
        # "sortBy=UPDATE_DATE&"
        # "pageNumber=1&sortDirection=false&recordsPerPage=_10&"
        # "showLotsInfoHidden=false",
        # "regions": {
        #     # "44000000000": "Костромская область",
        # },
        # "fallback_dates": {
        #     "from": "01.01.2026",
        #     "to": "30.02.2026",
        # },
        # "price": (1, 100000000000),
        # "max_span_contracts": 3000, # для разбивки диапазонов цен
        # "db_limit_max_span_contracts": 5000, # для определения количества страниц с контрактами
        # "default_per_page_items": 10,
        #
        # "default_proxy": None,
        # "query_params": QueryParams,
        # "dwl_stages": {
        #     "price_spans": "1_price_spans",
        #     "contracts_pages": "2_conatract_lists_pages",
        #     "contracts_data": "3_contracts_data",
        # },
        # "contracts_file_processed_mark": "processed_",
        # "default_fetch_contracts_concurency": 1,
    },

}

