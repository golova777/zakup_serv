import asyncio

import zakup_serv.settings as core_settings
from zakup_serv.domain.actual_contracts.query_parameters.pages import Page, PerPage
from zakup_serv.domain.actual_contracts.query_parameters.regions import ContractRegions
from zakup_serv.domain.actual_contracts.query_parameters.dates import StartDate, EndDate
from zakup_serv.domain.actual_contracts.query_parameters.prices import MinPrice, MaxPrice
from zakup_serv.domain.actual_contracts.urls import URLRequest
from zakup_serv.infrastructure.result_processors.save_on_disk import SaveOnDisk
from zakup_serv.settings import DEFAULT_TARGET_URLS
from zakup_serv.transport.aiohttp_dl import AiohttpDlTransport
from zakup_serv.transport.base import WebLoaderConfig


async def async_main():

    # =======скачивание контрактов (страницы пагинации)
    # 1. подготовить данные для пула запросов (города, дата-интервал, иные параметры)
    regions = ContractRegions(core_settings.contract_search_regions).regions
    start_date = StartDate("01.01.2026")
    end_date = EndDate("30.03.2026")
    min_price = MinPrice(core_settings.search_min_max_price[0])
    max_price = MaxPrice(core_settings.search_min_max_price[1])

    # 2. для каждого набора (город-даты) найти правильные интервалы пагинации

    urls = []
    for region in regions:
        url = URLRequest(DEFAULT_TARGET_URLS['CONTRACTS_44_FZ'])

        url.set_params(
            region.query_param,
            start_date.query_param,
            end_date.query_param,
            min_price.query_param,
            max_price.query_param,
            PerPage(200).query_param,
        )

        for i in range(15):
            _url = url.copy_url()
            _url.set_params(Page(i + 1).query_param)
            urls.append(_url)


    web_loader_config = WebLoaderConfig(
        [*urls],
        callback_on_instant_result=SaveOnDisk().async_save,
    )

    page_loader = AiohttpDlTransport(web_loader_config)
    results = await page_loader.async_fetch_pages()

    print(len(results))

    # print(web_loader_config)

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


if __name__ == '__main__':
    asyncio.run(async_main())