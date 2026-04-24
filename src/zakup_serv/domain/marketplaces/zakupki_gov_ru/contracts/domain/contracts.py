import asyncio
import logging
import os
import ast
from concurrent.futures import ProcessPoolExecutor
from os.path import isdir
from pathlib import Path
from pprint import pprint
from typing import Callable, Any, Iterator

import aiofiles
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
from zakup_serv.infrastructure.result_processors.decorators import net_stat_info

from zakup_serv.infrastructure.result_processors.extract_contract_nums import ContractNumsExtractor
from zakup_serv.infrastructure.result_processors.save_on_disk import SaveAnyOnDisk
from zakup_serv.settings import NET_DEFAULTS, SAVERS_DEFAULTS
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
            self.prepare_web_loader_configs()
        )


    def prepare_single_web_loader_config(self, target: dict) -> WebLoaderConfig:
        url = URLRequest(self.marketplace_config["base_url"])

        region = ContractRegions(
            {target["region_name"]: target["region_id"]}
        ).regions[0]

        url.set_query_params(
            region,
            StartDate(target['date_from']),
            EndDate(target['date_to']),
            PerPage(target['per_page_items']),
            Page(self.marketplace_config["default_page_num"]),
        )

        # установим иерархию сохранения файлов

        dir1 = "contracts_lists"
        dir2 = "_".join([target['date_from'], target['date_to']])
        dir3 = "_".join([target['region_id'], target['region_name']])
        url.save_directories.extend([dir1, dir2])

        web_config = WebLoaderConfig(
            [
                url,
            ],
        )

        return web_config

    @net_stat_info()
    def prepare_web_loader_configs(self) -> list[WebLoaderConfig]:

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

    @net_stat_info()
    async def a_get_current_region_price_spans(self, config: WebLoaderConfig) -> list:

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
                    self.a_fetch_page(
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
        filename = f"{region_id}_{region_name}.txt"
        await self.a_save_data_to_file(
            result_prices_spans,
            filename,
            folders=[
                self.marketplace_config['dwl_stages']['price_spans'],
                f"{self.from_date}_{self.to_date}",
            ]
        )

        return result_prices_spans

    @staticmethod
    @net_stat_info()
    async def a_save_data_to_file(
            data: Any,
            filename: str,
            folders: list[str] | None = None
    ) -> int:
        written = await SaveAnyOnDisk().a_process_it(str(data), filename, folders)
        logger.info(
            f"Data (type: {type(data)}) (len={written}) saved in file: {filename}"
        )
        return written


    async def _a_get_target_span_files_data(
            self,
            target_dir: Path
    ) -> list[dict]:

        async def _read_one_file(path: Path) -> str:
            async with aiofiles.open(path, mode="r", encoding="utf-8") as f:
                return await f.read()

        def walk_tree(root: str | Path, include_dirs: bool = False) -> Iterator[Path]:
            """
            Обходит дерево директорий от `root` вниз.

            :param root: корневая папка
            :param include_dirs: если True, возвращает и папки тоже
            :return: итератор Path-объектов
            """
            root = Path(root)

            for dirpath, dirnames, filenames in os.walk(root):
                current_dir = Path(dirpath)

                if include_dirs:
                    for d in dirnames:
                        yield current_dir / d

                for f in filenames:
                    yield current_dir / f

        # прочитать директории с ценовыми промежутками
        # для регионов для текущих дат from_date и to_date
        found_target_dir = None
        found_target_files = []
        targets = []

        for p in walk_tree(target_dir, include_dirs=True):
            if p.is_dir() and p.name == f"{self.from_date}_{self.to_date}":
                found_target_dir = p

                for file_obj in walk_tree(found_target_dir):
                    found_target_files.append(file_obj)

        if len(found_target_files) == 0:
            #  файлов для обработки не нашлось - останов
            raise RuntimeError("Nothing to do (no files)... Exiting...")

        tasks = [asyncio.create_task(_read_one_file(path)) for path in found_target_files]

        results = await asyncio.gather(*tasks)

        for result, file_obj in zip(results, found_target_files):
            # print(f"Read data: {result}")
            result = ast.literal_eval(result)
            region_id = file_obj.name.split("_")[0]
            region_name = file_obj.name.split("_")[1]

            targets.append({
                "region_id": region_id,
                "region_name": region_name,
                "file_name": file_obj.name,
                "file": file_obj,
                "data": list(result),
                "length": len(result),
                "date_from": self.from_date,
                "date_to": self.to_date,
                "per_page_items": self.per_page_items,
            })

        return targets

    async def _a_iterate_pages_search_contracts(
            self,
            web_config: WebLoaderConfig,
            price_from: int,
            price_to: int,
            start_page: int = 1,
            per_page_items: int = 50,
            save_dirs: list[str] | None = None,
    ) -> list[str]:
        # Здесь будет идти последовательный перебор страниц
        # с проверокй на наличие контрактов
        region_id = web_config.urls[0].region_id
        date_from = web_config.urls[0].date_from
        date_to = web_config.urls[0].date_to

        max_pages = int(
            self.marketplace_config["max_span_contracts"] / per_page_items
        )
        contract_numbers = []

        for page_number in range(start_page, max_pages+1):
            logger.info(f"Start page number: {page_number} "
                        f"for region {web_config.urls[0].region_id} "
                        f"for price span {price_from} to {price_to}")

            url_result = await self.a_fetch_page(
                deepcopy(web_config),
                page=page_number,
                price_from=price_from,
                price_to=price_to
            )
            contracts_list = await asyncio.to_thread(ContractNumsExtractor.get_contracts, url_result)

            if len(contracts_list) == 0:
                # нет больше контрактов
                logger.info(f"No more contracts on page {page_number} "
                            f"for region {web_config.urls[0].region_id} "
                            f"for price span {price_from} to {price_to}")
                break
            else:
                # есть контракты
                contract_numbers.extend(contracts_list)

                # сохраним страницу на диск
                # await SaveAnyOnDisk.a_process_it(
                #     url_result.request_result,
                #     f"{region_id}_date_{date_from}_{date_to}_price_{price_from}_{price_to}_page_{page_number}.txt",
                #     folders=save_dirs
                # )

        # сохраним только номера контрактов на диск
        await SaveAnyOnDisk.a_process_it(
            contract_numbers,
            f"{region_id}_date_{date_from}_{date_to}_price_{price_from}_{price_to}_counts_{len(contract_numbers)}.txt",
            folders=save_dirs
        )
        # это список контрактов для ценового диапазона
        # для конкретного региона в определенный диапазон дат
        return contract_numbers


    async def _get_exact_contracts_pages_on_span(
            self,
            target: dict,
            web_config: WebLoaderConfig,
    ):
            total_contracts_list = []

            # для каждого ценового диапазона скачиваем страницы пагинации
            tasks = [
                asyncio.create_task(
                    self._a_iterate_pages_search_contracts(
                        deepcopy(web_config),
                        price_from=span[0],
                        price_to=span[1],
                        start_page = 1,
                        per_page_items = target['per_page_items'],
                        save_dirs=target['save_dirs'],
                    )
                )
                for span in target['data']
                # for span in [target['data'][3],]
            ]

            contract_lists = await asyncio.gather(*tasks, return_exceptions=True)

            for contracts in contract_lists:
                if type(contracts) is list and len(contracts) > 0:
                    total_contracts_list.extend(contracts)
                else:
                    raise RuntimeError(f"ERROR: strange contract list: {type(contracts)} "
                                       f"with content {contracts}")

            # сохраним список контрактов
            # await SaveAnyOnDisk.a_process_it(
            #     total_contracts_list,
            #     f"{target['region_id']}_contracts_numbers_{len(total_contracts_list)}.txt",
            #     folders=target['save_dirs']
            #
            # )

            logger.info(
                f"Fetched {len(total_contracts_list)} contract numbers "
                f"for contracts pages for region "
                f"{target['region_name']} (id: {target['region_id']})"
            )

            return total_contracts_list


    async def a_get_all_contract_lists_pages(
            self,
            per_page_items: int = MARKETPLACE_INFO["44FZ"]['default_per_page_items']
    ):

        target_dir = (
                Path(SAVERS_DEFAULTS["SAVE_FOLDER"]) /
                Path(self.marketplace_config['dwl_stages']['price_spans'])
        )
        targets = await self._a_get_target_span_files_data(target_dir)

        for target in targets:
            logger.info(f"Start getting contract pages for region {target['region_name']} "
                        f"(id: {target['region_id']})")

            target['per_page_items'] = per_page_items
            target['save_dirs'] = [
                '2_conatract_lists_pages',
                f'{target["date_from"]}_{target["date_to"]}',
                f'{target["region_id"]}'
            ]

            web_loader_config = self.prepare_single_web_loader_config(target)
            # pprint(web_loader_config)
            res = await self._get_exact_contracts_pages_on_span(target, web_loader_config)

            pprint(res)



    async def a_get_all_region_price_spans(self):
        # Ограничение конкурентности ################################
        concur_connects = NET_DEFAULTS["CONCURRENT_CONNECTIONS"]
        semaphore = asyncio.Semaphore(concur_connects)

        async def semaphore_get_region_price_spans(config):
            async with semaphore:
                return await self.a_get_current_region_price_spans(config)

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

    async def a_fetch_page(
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
