import zakup_serv.settings as core_settings
from zakup_serv.domain.actual_contracts.regions import ContractRegions
from zakup_serv.domain.actual_contracts.date_interval import DateInterval
from zakup_serv.domain.actual_contracts.price_interval import PriceInterval
from zakup_serv.transport.base import WebLoaderConfig, WebLoader

if __name__ == '__main__':
    target_url = "https://zakupki.gov.ru/epz/contract/search/results.html?searchString=&morphology=on&search-filter=%D0%94%D0%B0%D1%82%D0%B5+%D0%BE%D0%B1%D0%BD%D0%BE%D0%B2%D0%BB%D0%B5%D0%BD%D0%B8%D1%8F&savedSearchSettingsIdHidden=&fz44=on&contractStageList_0=on&contractStageList_1=on&contractStageList_2=on&contractStageList_3=on&contractStageList=0%2C1%2C2%2C3&contractInputNameDefenseOrderNumber=&contractInputNameContractNumber=&contractPriceFrom=100000&rightPriceRurFrom=&priceFromUnitGWS=&contractPriceTo=101000&rightPriceRurTo=&priceToUnitGWS=&currencyCode=&nonBudgetCodesList=&budgetLevelsIdHidden=&budgetLevelsIdNameHidden=%7B%7D&budgetName=&customerPlace=44000000000&customerPlaceCodes=44000000000&contractDateFrom=01.01.2025&contractDateTo=&executionDateStart=31.12.2025&executionDateEnd=&publishDateFrom=&publishDateTo=&updateDateFrom=&updateDateTo=&placingWayList=&selectedLaws=&sortBy=UPDATE_DATE&pageNumber=1&sortDirection=false&recordsPerPage=_10&showLotsInfoHidden=false"

    # =======скачивание контрактов (страницы пагинации)
    # 1. подготовить данные для пула запросов (города, дата-интервал, иные параметры)
    regions = ContractRegions(core_settings.contract_search_regions)
    date_interval = DateInterval("01.01.2026", "31.03.2026")
    price_interval = PriceInterval(core_settings.search_min_max_price[0], core_settings.search_min_max_price[1])

    # request_data = RequestConstructor(regions, date_interval, price_interval)

    # 2. для каждого набора (город-даты) найти правильные интервалы пагинации

    web_loader_config = WebLoaderConfig(
        [target_url,],

    )





    # 3. для каждого набора (город-даты-интервал пагинации) скачать и сохранить страницы списка контрактов
    # 4. Парсинг: извлечь номера контрактов (ссылки) - сохранить в файл построчно
    #   4.1 сохраним файлы страниц для последующего парсинга без скачивания
    # 5. скачивать контракты по сслыкам (как хранить файлы документации???)
    #   5.1 проверить иредварительно наличие скачанного контракта
    # 6. извлечь данные о контрактах в БД, файлы сохранить
    #
    # надо предусмотреть возможность сразу проверять номера контрактов в скачанных
    # страницах пагинации - чтиобы оставнавливать скачивание если уже все закачано ранее
    # порядок сортировки скачивания старниц пагинации проверить - сначала надо самые свежие
    #
    #
from zakup_serv.transport.prepare_request import RequestConstructor



