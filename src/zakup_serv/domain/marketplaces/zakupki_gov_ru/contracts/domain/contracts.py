import asyncio
import logging
from concurrent.futures import ProcessPoolExecutor
from typing import Callable, Any
from bs4 import BeautifulSoup
from copy import deepcopy

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
from zakup_serv.infrastructure.result_processors.decorators import add_jitter_delay
from zakup_serv.infrastructure.result_processors.save_on_disk import SaveAnyOnDisk
from zakup_serv.settings import JITTER, NET_DEFAULTS
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
            dir1 = region.region_name
            dir2 = "_".join([self.from_date, self.to_date])
            url.save_directories.extend([dir1, dir2])

            web_config = WebLoaderConfig(
                [
                    url,
                ],
                callbacks_list_on_result=self.callbacks_on_result,
            )

            configs.append(web_config)

        return configs

    # @add_jitter_delay(JITTER['mu'], JITTER['std'])
    async def a_get_region_price_spans(self, config: WebLoaderConfig) -> list:

        # список диапазонов цен, где будем дробить диапазон
        # и после переносить из него подходящие диапазогны
        init_prices_spans = [list(self.marketplace_config["price"])]
        # результирующий список диапазонов цен, которые подходят по количеству контрактов
        result_prices_spans = []
        # максимально допустимое число контрактов на ценовой диапазон для того, чтобы его не дробить
        max_span_contracts = self.marketplace_config["max_span_contracts"]

        logger.info(
            f"Start search price spans for region "
            f"{config.urls[0].region_name}[id={config.urls[0].region_id}]"
        )
        while len(init_prices_spans) > 0:
            # print(result_prices_spans)
            # 1.  получить страницы для извлечения
            # количества контрактов для каждого диапазона цен
            tasks = [
                asyncio.create_task(
                    self.fetch_page(
                        deepcopy(config), price_from=span[0], price_to=span[1]
                    )
                )
                for span in init_prices_spans
            ]

            pass
            span_results_pages = await asyncio.gather(*tasks, return_exceptions=True)
            logger.info(
                f"Fetched {len(span_results_pages)} URLS for price spans for region "
                f"{config.urls[0].region_name}[id={config.urls[0].region_id}]"
            )

            # 2. отсеять интервалы цены для которых вместо страницы пришло исключение
            temp_price_spans = []
            temp_price_spans_pages = []
            for span, span_page in zip(init_prices_spans, span_results_pages):
                if isinstance(span_page.request_result, Exception):
                    logger.warning(
                        f"ERROR: for region {config.urls[0].region_name} "
                        f"(code:{config.urls[0].region_id}) "
                        f"span ({str(span)}) got exception [{type(span_page)}]"
                    )
                    continue
                # logger.info(f"for region {config.urls[0].region_name} "
                #                f"(code:{config.urls[0].region_id}) "
                #                f"span ({str(span)}) URL {span_page.url_request.result_url} ")
                temp_price_spans.append(span)
                temp_price_spans_pages.append(
                    span_page.request_result
                )  # сохраняем только контент страниц

            pass

            # 3. получим количество контрактов для каждого диапазона цен,
            # для которых успешно получили страницу
            with ProcessPoolExecutor() as pool:
                contracts_counts = list(
                    pool.map(self.get_total_contracts, temp_price_spans_pages)
                )

            # 4. обработка диапазонов цен в зависимости от количества контрактов в них
            for span, total_contracts in zip(temp_price_spans, contracts_counts):

                region_name = config.urls[0].region_name
                region_id = config.urls[0].region_id
                print(
                    f"For {region_name} (code={region_id}) "
                    f"span ({str(span)}) got {total_contracts} contracts"
                )

                if total_contracts == 0:
                    # В этом диапазоне контрактов нет - удалим его из начального списка
                    init_prices_spans.remove(span)
                    continue

                if total_contracts < max_span_contracts > 0:
                    # Этот диапазон цен дробить не надо - переносим его в result_prices_spans
                    result_prices_spans.append(span)  # добавим в результат
                    init_prices_spans.remove(span)  # удалим из начального списка
                else:
                    # Этот диапазон цен надо дробить -
                    # разделим его пополам и добавим обе половины обратно в init_prices_spans
                    mid_price = (span[0] + span[1]) // 2
                    new_span1 = [span[0], mid_price]
                    new_span2 = [mid_price + 1, span[1]]
                    init_prices_spans.append(new_span1)
                    init_prices_spans.append(new_span2)
                    init_prices_spans.remove(span)  # удалим из начального списка

        logger.info(
            f"Price_spans for region {config.urls[0].region_name}[id={config.urls[0].region_id}] "
            f"got results: \n{result_prices_spans}"
        )

        # запишем в файл
        region_id = config.urls[0].region_id
        region_name = config.urls[0].region_name
        date_from = config.urls[0].date_from
        date_to = config.urls[0].date_to
        filename = f"{region_id}_{date_from}_{date_to}.txt"
        await self.a_save_data_to_file(result_prices_spans, filename)

        return result_prices_spans

    async def a_save_data_to_file(self, data: Any, filename: str) -> int:
        written = await SaveAnyOnDisk().a_process_it(str(data), filename)
        logger.info(
            f"Data (type: {type(data)}) (len={written}) saved in file: {filename}"
        )
        return written

    async def a_get_all_contract_lists_pages(self):
        # Ограничение конкурентности ################################
        concur_connects = NET_DEFAULTS["CONCURRENT_CONNECTIONS"]
        semaphore = asyncio.Semaphore(concur_connects)

        async def semaphore_get_region_price_spans(config):
            async with semaphore:
                return await self.a_get_region_price_spans(config)

        ##############################################################

        try:
            tasks = [
                asyncio.create_task(semaphore_get_region_price_spans(config))
                for config in self.web_loader_configs
            ]

            spans_results = await asyncio.gather(*tasks, return_exceptions=True)

            error_count = 0
            for config, spans in zip(self.web_loader_configs, spans_results):

                if isinstance(spans, Exception):
                    error_count += 1
                    logger.warning(
                        f"ERROR: for region {config.urls[0].region_name} "
                        f"(code:{config.urls[0].region_id}) "
                        f"price spans got exception [{type(spans)}]"
                    )

            # логируем статистику выполнения
            logger.info(
                f"Downloaded spans {len(spans_results)}. With Errors: {error_count}"
            )

        except Exception as e:
            logger.exception(e)

    def get_total_contracts(self, raw_data) -> int:

        def clear_int(data: str) -> int:
            # print(data)
            data_int = int("".join([x for x in data if x.isdigit()]))
            # print(data_int)
            return data_int

        result = 0

        try:
            soup = BeautifulSoup(raw_data, "lxml")
            total_div = soup.find("div", class_="search-results__total")
            if total_div:
                result = clear_int(total_div.get_text(strip=True))
            else:
                logger.warning("Не найден div с классом search-results__total")

        except Exception as e:
            logger.info("No contracts number info on page!")
            return 0
        else:
            return result

    async def fetch_page(
        self,
        config: WebLoaderConfig,
        page: int | None = None,
        price_from: int | None = None,
        price_to: int | None = None,
    ) -> URLResult:

        page_loader = AiohttpDlTransport(config)
        set_param = page_loader.urls[0].set_query_params

        change_params = []  # список параметров ГКД которые надо поменять
        if page:
            change_params.append(Page(page))
        if price_from:
            change_params.append(MinPrice(price_from))
        if price_to:
            change_params.append(MaxPrice(price_to))

        set_param(*change_params)  # установим новые параметры для запроса

        download_results = await page_loader.a_run()

        logger.info(
            f"HTTP Status {download_results[0].url_request.status_code} for "
            # f"params: {change_params} . URL {download_results[0].url_request.result_url}"
            f"params: {change_params}"
        )

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
