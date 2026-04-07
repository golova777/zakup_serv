import zakup_serv.settings as core_settings
from zakup_serv.domain.actual_contracts.regions import ContractRegions
from zakup_serv.domain.actual_contracts.date_interval import DateInterval
from zakup_serv.domain.actual_contracts.price_interval import PriceInterval
from zakup_serv.transport.prepare_request import RequestConstructor


if __name__ == '__main__':

    # =======скачивание контрактов (страницы пагинации)
    # 1. подготовить данные для пула запросов (города, дата-интервал, иные параметры)
    regions = ContractRegions(core_settings.contract_search_regions)
    date_interval = DateInterval("01.01.2026", "31.03.2026")
    price_interval = PriceInterval(core_settings.search_min_max_price[0], core_settings.search_min_max_price[1])

    request = RequestConstructor(regions, date_interval, price_interval)

    # 2. для каждого набора (город-даты) найти правильные интервалы пагинации





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



