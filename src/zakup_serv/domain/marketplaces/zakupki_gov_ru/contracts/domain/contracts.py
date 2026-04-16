import asyncio
import logging
from typing import Callable

from bs4 import BeautifulSoup

from zakup_serv.domain.marketplaces.zakupki_gov_ru.config import MARKETPLACE_INFO
from zakup_serv.domain.marketplaces.zakupki_gov_ru.contracts.query_parameters.dates import (
    StartDate,
    EndDate,
)
from zakup_serv.domain.marketplaces.zakupki_gov_ru.contracts.query_parameters.pages import (
    PerPage,
    Page,
)
from zakup_serv.domain.marketplaces.zakupki_gov_ru.contracts.query_parameters.prices import (
    MinPrice,
    MaxPrice,
)
from zakup_serv.domain.marketplaces.zakupki_gov_ru.contracts.query_parameters.regions import (
    ContractRegions,
)
from zakup_serv.domain.marketplaces.zakupki_gov_ru.contracts.urls import (
    URLRequest,
    URLResult,
)
from zakup_serv.transport.aiohttp_dl import AiohttpDlTransport
from zakup_serv.transport.base import WebLoaderConfig

# Подключим логирование
logger = logging.getLogger(__name__)

"""
взодящие параметры
список регионов (или один регион)
дата выборки (от и до)

"""


class FZ44_ContractsLists:
    def __init__(
        self,
        regions: dict[str, str] = None,
        from_date: str = None,
        to_date: str = None,
        per_page_items: int | None = None,
        callbacks_on_result: list[Callable] | None = None,
        marketplace_config: dict = MARKETPLACE_INFO["44FZ"],
    ):
        # конфиг площадки
        self.marketplace_config = marketplace_config

        self.regions: dict[str, str] = (
            regions if regions else self.marketplace_config["regions"]
        )
        self.from_date: str = (
            from_date
            if from_date
            else self.marketplace_config["fallback_dates"]["from"]
        )
        self.to_date: str = (
            to_date if to_date else self.marketplace_config["fallback_dates"]["to"]
        )
        self.per_page_items: int = (
            per_page_items
            if per_page_items
            else self.marketplace_config["default_per_page_items"]
        )
        self.callbacks_on_result: list[Callable] = (
            callbacks_on_result if callbacks_on_result else []
        )

        # Конфиги для каждого Региона+Диапазон дат
        self.web_loader_configs: list[WebLoaderConfig] = (
            self.prepare_web_loader_config()
        )

    def prepare_web_loader_config(self) -> list[WebLoaderConfig]:

        regions = ContractRegions(self.regions).regions

        configs = []

        for region in regions:
            url = URLRequest(self.marketplace_config["base_url"])

            url.set_query_params(
                region,
                StartDate(self.from_date),
                EndDate(self.to_date),
                MinPrice(self.marketplace_config["price"][0]),
                MaxPrice(self.marketplace_config["price"][1]),
                PerPage(self.per_page_items),
                Page(1),
            )

            # установим иерархию сохранения файлов
            dir1 = region.name
            dir2 = "_".join([self.from_date, self.to_date])
            url.save_directories.extend([dir1, dir2])

            web_config = WebLoaderConfig(
                [
                    url,
                ],
                callbacks_list_on_result=self.callbacks_on_result,
            )

            configs.append(web_config)
            print(configs)

        return configs

    async def a_get_all_contract_lists_pages(self):

        for config in self.web_loader_configs:

            res = await self.fench_one_page(5, config)
            num_contracts = await asyncio.to_thread(self.get_estimate_num_contracts, res.request_result)

            # TODO сделать бинарный посик диапазонов цены контракта

            print(num_contracts)

        logger.info(f"Работа завершена. {res.url_request.status_code}")

    def get_estimate_num_contracts(self, raw_data) -> int:

        def clear_int(data: str) -> int:
            print(data)
            data_int = int("".join([x for x in data if x.isdigit()]))
            print(data_int)
            return data_int

        result = 0

        soup = BeautifulSoup(raw_data, "lxml")
        total_div = soup.find("div", class_="search-results__total")
        if total_div:
            result = clear_int(total_div.get_text(strip=True))
        else:
            logger.warning("Не найден div с классом search-results__total")

        return result

    async def fench_one_page(self, page: int, config: WebLoaderConfig) -> URLResult:
        page_loader = AiohttpDlTransport(config)
        set_page = page_loader.urls[0].set_query_params
        set_page(Page(page))

        download_results = await page_loader.a_run()

        logger.info(f"URL: {download_results[0].url_request.result_url} результатов.")

        return download_results[0]


"""
 # =======скачивание контрактов (страницы пагинации)
    # 1. подготовить данные для пула запросов (города, дата-интервал, иные параметры)

    regions = ContractRegions(core_settings.contract_search_regions).regions
    start_date = StartDate("01.01.2026")
    end_date = EndDate("30.03.2026")
    min_price = MinPrice(core_settings.search_min_max_price[0])
    max_price = MaxPrice(core_settings.search_min_max_price[1])

    # обработчики результатов запросов страниц
    result_processors = [
        # ResponseLength().a_process_it,
        # ResponseLength().process_it,
        # SaveOnDisk().a_process_it,
        # ContractNumsExtractor().a_process_it,
        ContractNumsExtractor().process_it,
    ]

    # 2. для каждого набора (город-даты) найти правильные интервалы пагинации

    urls = []
    for region in regions:
        url = URLRequest(DEFAULT_TARGET_URLS["CONTRACTS_44_FZ"])

        url.set_params(
            region.query_param,
            start_date.query_param,
            end_date.query_param,
            min_price.query_param,
            max_price.query_param,
            PerPage(200).query_param,
        )

        for i in range(3):
            _url = url.copy_url()
            _url.set_params(Page(i + 1).query_param)
            urls.append(_url)

    web_loader_config = WebLoaderConfig(
        [*urls],
        callbacks_list_on_result=result_processors,
        proxy=core_settings.DEFAULTS.get("PROXY", None),
    )

    page_loader = AiohttpDlTransport(web_loader_config)
    download_results = await page_loader.a_run()

    logger.info(f"Работа завершена. Получено {len(download_results)} результатов.")

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


"""
