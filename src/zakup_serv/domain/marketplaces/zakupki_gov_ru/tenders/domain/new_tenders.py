import asyncio
import logging
import os
import ast
import re
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path
from pprint import pprint
from typing import Callable, Any, Iterator

import aiofiles
from bs4 import BeautifulSoup
from copy import deepcopy

from zakup_serv.domain.marketplaces.zakupki_gov_ru.tenders.query_parameters.dates import StartDate
from zakup_serv.domain.marketplaces.zakupki_gov_ru.tenders.query_parameters.pages import PerPage, Page
from zakup_serv.domain.marketplaces.zakupki_gov_ru.tenders.query_parameters.regions import Regions
from zakup_serv.domain.marketplaces.zakupki_gov_ru.tenders.tender_config import TENDER_MARKETPLACE_INFO
from zakup_serv.infrastructure.urls import URLRequest
from zakup_serv.transport.base import WebLoaderConfig

# from zakup_serv.domain.marketplaces.zakupki_gov_ru.contracts.contract_config import MARKETPLACE_INFO
# from zakup_serv.domain.marketplaces.zakupki_gov_ru.contracts.query_parameters.base import QueryParam
# from zakup_serv.domain.marketplaces.zakupki_gov_ru.contracts.query_parameters.dates import (
#     StartDate,
#     EndDate,
# )
# from zakup_serv.domain.marketplaces.zakupki_gov_ru.contracts.query_parameters.pages import (
#     PerPage,
#     Page,
# )
# from zakup_serv.domain.marketplaces.zakupki_gov_ru.contracts.query_parameters.prices import (
#     MinPrice,
#     MaxPrice,
# )
# from zakup_serv.domain.marketplaces.zakupki_gov_ru.contracts.query_parameters.reestr_number import ReestrNumber
# from zakup_serv.domain.marketplaces.zakupki_gov_ru.contracts.query_parameters.regions import (
#     ContractRegions,
# )
# from zakup_serv.domain.marketplaces.zakupki_gov_ru.contracts.urls import (
#     URLRequest,
#     URLResult,
# )
# from zakup_serv.infrastructure.result_processors.decorators import net_stat_info
#
# from zakup_serv.infrastructure.result_processors.extract_contract_nums import ContractNumsExtractor
# from zakup_serv.infrastructure.result_processors.save_on_disk import SaveAnyOnDisk
# from zakup_serv.settings import NET_DEFAULTS, SAVERS_DEFAULTS
# from zakup_serv.transport.aiohttp_dl import AiohttpDlTransport
# from zakup_serv.transport.base import WebLoaderConfig

# Подключим логирование
logger = logging.getLogger(__name__)

"""
взодящие параметры
список регионов (или один регион)
дата выборки (от и до)

"""


class FzNewTenders:
    def __init__(
        self,
        regions: dict[str, str] = None,
        from_date: str = None,
        to_date: str = None,
        per_page_items: int | None = None,
        callbacks_on_result: list[Callable] | None = None,
        marketplace_config: dict = TENDER_MARKETPLACE_INFO["EIS"],
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


    def _set_contracts_single_web_loader_config(self, target: dict, link: str) -> WebLoaderConfig:
        # target_contract = {
        #     "region_id": region_dir.name,
        #     "number": contract_num,
        #     "file_name": curr_file.name,
        #     "file": curr_file,
        #     "processed_file_name": f"{processed_suffix}{curr_file.name}",
        #     "processed_file": curr_file.with_name(f"{processed_suffix}{curr_file.name}"),
        #     "date_from": self.from_date,
        #     "date_to": self.to_date,
        #     "save_dirs": [],
        # }

        url = URLRequest(link)

        url.set_query_params(
            ReestrNumber(target['number']),
        )

        web_config = WebLoaderConfig(
            [
                url,
            ],
        )

        return web_config


    def _set_tender_pages_single_web_loader_config(self, target: dict) -> WebLoaderConfig:

        url = URLRequest(self.marketplace_config["base_url"])

        region = Regions(
            {target["region_id"]: target["region_name"]}
        ).regions[0]

        url.set_query_params(
            region,
            StartDate(target['date_from']),
            # EndDate(target['date_to']),
            PerPage(target['per_page_items']),
            Page(self.marketplace_config["default_page_num"]),
        )

        # установим иерархию сохранения файлов

        dir1 = "tenders_lists"
        dir2 = target['date_from']
        dir3 = "_".join([target['region_id'], target['region_name']])
        url.save_directories.extend([dir1, dir2, dir3])

        web_config = WebLoaderConfig(
            [
                url,
            ],
        )

        return web_config


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
                    self._a_fetch_page(
                        deepcopy(config),
                        [
                            MinPrice(span[0]),
                            MaxPrice(span[1])
                        ],
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

            # TODO а стоит ли их прсто отсевать если пришло исключение????
            #  там ведь дланные могут быть всё равно
            # 2. отсеять интервалы цены для которых вместо страницы пришло исключение
            temp_price_spans = []
            temp_price_spans_pages = []
            temp_price_spans_data = []
            temp_price_spans_and_num_contracts = {}
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
                temp_price_spans_data.append(
                    span_page
                )

            # 3. получим количество контрактов для каждого диапазона цен,
            # для которых успешно получили страницу
            with ProcessPoolExecutor() as pool:
                contracts_counts = list(
                    pool.map(self._get_total_contracts, temp_price_spans_pages)
                )

            # 4. обработка диапазонов цен в зависимости от количества контрактов в них
            for span, total_contracts, url_result in zip(temp_price_spans, contracts_counts, temp_price_spans_data):

                region_name = config.urls[0].region_name
                region_id = config.urls[0].region_id
                print(
                    f"For {region_name} (code={region_id}) "
                    f"span ({str(span)}) got {total_contracts} contracts "
                    # f"URL: {url_result.url_request.result_url if url_result.url_request else 'N/A'}"
                )

                if total_contracts == 0:
                    # В этом диапазоне контрактов нет - удалим его из начального списка
                    init_prices_spans.remove(span)
                    continue

                if total_contracts < max_span_contracts > 0:
                    # Этот диапазон цен дробить не надо - переносим его в result_prices_spans
                    result_prices_spans.append(span)  # добавим в результат
                    init_prices_spans.remove(span)  # удалим из начального списка
                    temp_price_spans_and_num_contracts[total_contracts] = span
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
        await self._a_save_data_to_file(
            # TODO вместо result_prices_spans нужно сделать вызов как на следующей строке
            # self._normalize_price_spans(temp_price_spans_and_num_contracts),
            result_prices_spans,
            filename,
            folders=[
                self.marketplace_config['dwl_stages']['price_spans'],
                f"{self.from_date}_{self.to_date}",
            ]
        )

        return result_prices_spans

    @staticmethod
    def _normalize_price_spans(price_spans: list[list]) -> list[list]:
        # TODO сделать нормализацию списка промежутков цен.

        return price_spans


    @staticmethod
    @net_stat_info()
    async def _a_save_data_to_file(
            data: Any,
            filename: str,
            folders: list[str | Path] | Path | None = None,
    ) -> int:
        written = await SaveAnyOnDisk().a_process_it(str(data), filename, folders)
        logger.info(
            f"Data (type: {type(data)}) (len={written}) saved in file: {filename}"
        )
        return written

    @staticmethod
    def _walk_dir_tree(
            root: str | Path,
            include_dirs: bool = False,
            include_files: bool = True,
            filter_dirs: list[str] | None = None,
    ) -> Iterator[Path]:
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
                    if filter_dirs:
                        if d in filter_dirs:
                            yield current_dir / d
                    else:
                        yield current_dir / d
            if include_files:
                for f in filenames:
                    yield current_dir / f


    @staticmethod
    async def _read_one_file(path: Path) -> str:
        ''' вернёт содержимое файла асинхронно'''
        async with aiofiles.open(path, mode="r", encoding="utf-8") as f:
            return await f.read()


    async def _a_get_target_span_files_data(
            self,
            target_dir: Path
    ) -> list[dict]:
        # прочитать директории с ценовыми промежутками
        # для регионов для текущих дат from_date и to_date
        found_target_dir = None
        found_target_files = []
        targets = []

        for p in self._walk_dir_tree(target_dir, include_dirs=True):
            if p.is_dir() and p.name == f"{self.from_date}_{self.to_date}":
                found_target_dir = p

                for file_obj in self._walk_dir_tree(found_target_dir):
                    found_target_files.append(file_obj)

        if len(found_target_files) == 0:
            #  файлов для обработки не нашлось - останов
            raise RuntimeError("Nothing to do (no files)... Exiting...")

        tasks = [asyncio.create_task(self._read_one_file(path)) for path in found_target_files]

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
            self.marketplace_config["db_limit_max_span_contracts"] / per_page_items
        )
        contract_numbers = []

        for page_number in range(start_page, max_pages+1):

            url_result = await self._a_fetch_page(
                deepcopy(web_config),
                [
                    Page(page_number),
                    MinPrice(price_from),
                    MaxPrice(price_to),
                ],
            )
            logger.info(f"Start page number: {page_number} "
                        f"for region {web_config.urls[0].region_id} "
                        f"for price span {price_from} to {price_to} "
                        # f"URL: {url_result.url_request.result_url}"
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


    async def _get_tenders(
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


    async def a_get_tenders_pages(
            self,
            per_page_items: int | None = None,
    ):
        per_page_items = per_page_items or self.marketplace_config['default_per_page_items']

        # 1. выполним конкурентно поиск закупок для N регионов asyncio.gather...
        # 2. для конкретного региона поиск выполняется последовательно - постранично (синхронно)
        # 2.1. задаём бесконечный генератор страниц и скачиваем страницу
        # 2.2. выделяем номера закупок и запрашиваем из репозитория  (его надо создать) закупок - какие уже присутствуют
        # 2.3. отсеваем присутствующие в репозитории закупки.
        # 2.4. Если осталось 0 закупок, то прекращаем итерации по страницам закупок региона - новых нет
        # 2.5. после отсева остались закупки
        # 2.5.1. складываем все новые закупки в общий список NewTenders[]
        # 3. завершились поиски закупок по всем регионам
        # 4. скачиваем все новые закупки (полностью) и сохраняем через репозиторий
        #
        #
        #
        #
        #
        #

        for region_id, region_name in self.regions.items():
            logger.info(f"Start getting tenders pages for region {region_name} "
                        f"(id: {region_id})")
            target = dict()

            target["region_id"] = region_id
            target["region_name"] = region_name
            target['per_page_items'] = per_page_items
            target['save_dirs'] = [
                self.marketplace_config['dwl_stages']['tenders_pages'],
                f'{target["date_from"]}',
                f'{target["region_id"]}'
            ]

            web_loader_config = self._set_tender_pages_single_web_loader_config(target)
            pprint(web_loader_config)
            res = await self._get_tenders(target, web_loader_config)

            pprint(res)



    async def a_get_price_spans(
            self,
            concurrent: int | None = None
    ):
        # Ограничение конкурентности ################################
        concur_connects = concurrent or NET_DEFAULTS["CONCURRENT_CONNECTIONS"]
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

    @staticmethod
    def _get_total_contracts(raw_data) -> int:

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

    @net_stat_info()
    async def _a_fetch_contract_data(self, target_contract: dict) -> dict:
        # нужно несколько этапов получения данных контракта
        # 1. основные страницы из реестра контрактов
        # 2. с основных страниц контракта: ссылки на вложенные файлы, на закупку, реестр недобросовестных
        # 3. со страницы закупки: вложенные файлы

        ###################################################
        # Фаза 1 основные страницы из реестра контрактов
        links_phase_1 = {
            "contract_common_info": "https://zakupki.gov.ru/epz/contract/contractCard/common-info.html?reestrNumber=_",
            "contract_payments": "https://zakupki.gov.ru/epz/contract/contractCard/payment-info-and-target-of-order.html?reestrNumber=_",
            "contract_execution": "https://zakupki.gov.ru/epz/contract/contractCard/process-info.html?reestrNumber=_",
            "contract_attachments": "https://zakupki.gov.ru/epz/contract/contractCard/document-info.html?reestrNumber=_",
            "contract_versions": "https://zakupki.gov.ru/epz/contract/contractCard/journal-version.html?reestrNumber=_",
            "contract_logs": "https://zakupki.gov.ru/epz/contract/contractCard/event-journal.html?reestrNumber=_",
        }

        # query параметр номера контракта в реестре
        reestr_num_param = ReestrNumber(target_contract['number'])

        configs_phase_1 = []
        tasks_phase_1 = []
        coro_phase_1 = []

        for section, link in links_phase_1.items():
            config = self._set_contracts_single_web_loader_config(target_contract, link)
            configs_phase_1.append(config)
            task = asyncio.create_task(self._a_fetch_page(config, [reestr_num_param]))
            tasks_phase_1.append(task)

            coro = self._a_fetch_page(config, [reestr_num_param])
            coro_phase_1.append(coro)

            ########################
            res = await coro

            print(len(res.request_result))
            ########################

            await self._a_save_data_to_file(
                res.request_result,
                f"{target_contract['number']}_{section}.txt",
                target_contract['save_dirs'])





        # results = asyncio.gather(*tasks_phase_1, return_exceptions=True)

        # for result, config, section in zip(results, configs_phase_1, links_phase_1.keys()):
        #     if isinstance(result, Exception):
        #         result_exception = result
        #         logger.error(f"Failed fetching contract num {target_contract['number']} "
        #                      f"for region {target_contract['region_id']} "
        #                      f"section {section} "
        #                      f"with exception {type(result)} "
        #                      f"{result}")
        #
        #         # Ошибка при загрузке секций контракта - отмена дальнейшей загрузки
        #         raise FailedContractFetchException(
        #             target_contract['number'],
        #             type(result_exception),
        #             f"section {section} and URL {config.urls[0].result_url} "
        #         )
        #
        #     # TODO пеервести в debug в последствие
        #     logger.info(f"Fetched section {section} (len={len(result)})"
        #                  f"for contract num {target_contract['number']} "
        #                  f"with URL {config.urls[0].result_url}")
        #
        # # первая фаза контракта скачана полностью
        # logger.info(f"Successfully fetched contract num {target_contract['number']} "
        #             f"for region {target_contract['region_id']} ")
        #
        # # сохраним файлы 1 фазы на диск
        # for result, config, section in zip(results, configs_phase_1, links_phase_1.keys()):
        #     await self._a_save_data_to_file(
        #         result,
        #         f"{target_contract['number']}_{section}.txt",
        #         target_contract['save_dirs'])


        return {
            "file_name": target_contract['file_name'],
        }




    async def a_get_contracts_data(
            self,
            concurrent: int = 1,
            force_reprocessed_files: bool = False
    ):

        def replace_counts_in_filename(filename: str, new_count: int | str) -> str:
            """
            Меняет число после `counts_` в имени файла.

            Пример:
            44000000000_date_01.01.2024_31.12.2024_price_1_95368_counts_4245.txt
            -> ..._counts_1000.txt
            """
            pattern = r"(counts_)\d+"
            return re.sub(pattern, rf"\g<1>{new_count}", filename)


        concurrent = concurrent or self.marketplace_config['default_fetch_contracts_concurency']
        processed_suffix = self.marketplace_config['contracts_file_processed_mark']

        #####################################################################
        # 1. Определить целевую папку, где лежат файлы с номерами контрактов
        target_dir = (
                Path(SAVERS_DEFAULTS["SAVE_FOLDER"]) /
                Path(self.marketplace_config['dwl_stages']['contracts_pages']) /
                Path(f"{self.from_date}_{self.to_date}")
        )

        #####################################################################
        # 2. получим папки для каждого региона,
        # для которого скачаны номера контрактов
        region_dirs = self._walk_dir_tree(
            target_dir,
            include_dirs=True,
            include_files=False,
            filter_dirs=list(self.regions.keys()),
        )

        #####################################################################
        # 3. для каждого региона получим список файлов с номерами контрактов
        for region_dir in region_dirs:
            contract_files = self._walk_dir_tree(
                region_dir,
                include_dirs=False,
                include_files=True,
            )

            # Список контрактов которые не удалось скачать
            region_fetch_failed_contracts = []

            #####################################################################
            # 4. для каждого файла с номерами контрактов
            # получим эти номера и сохраним их в виде списка
            for curr_file in contract_files:

                # curr_file - этот файл
                # при полной обработке контрактов надо обновить префиксом "processed_"
                if not force_reprocessed_files:
                    # пропускаем файлы контрактов с отметкой "processed_",
                    # если нет режима принудительной обработки ранее обработанных файлов
                    if processed_suffix in curr_file.name:
                        logger.info(f"Skipping already processed {curr_file.name}")
                        continue

                # список номеров контрактов
                contracts_nums = await self._read_one_file(curr_file)
                contracts_nums = ast.literal_eval(contracts_nums)

                total_span_contracts = len(contracts_nums)

                #####################################################################
                # 5. составим список contract_targets
                # - словарей с данными для обработки каждого контракта
                contract_targets = []
                for contract_num in contracts_nums[:]:
                    #  Итерируем по списку номеров контрактов
                    #  - добавляя в писко целей
                    target_contract = {
                        "region_id": region_dir.name,
                        "number": contract_num,
                        "file_name": curr_file.name,
                        "file": curr_file,
                        "processed_file_name": f"{processed_suffix}{curr_file.name}",
                        "processed_file": curr_file.with_name(f"{processed_suffix}{curr_file.name}"),
                        "date_from": self.from_date,
                        "date_to": self.to_date,
                        "save_dirs": [
                            self.marketplace_config['dwl_stages']['contracts_data'],
                            f"{self.from_date}_{self.to_date}",
                            f"{region_dir.name}",
                            f"{contract_num}",
                        ],
                    }
                    contract_targets.append(target_contract)

                #####################################################ё################
                # 6. конкурентно скачаем данные для каждого контракта из файла
                semaphore = asyncio.Semaphore(concurrent)

                async def semaphore_a_fetch_contract_data(target: dict):
                    async with semaphore:
                        return await self._a_fetch_contract_data(target)

                fetch_contracts_tasks = [
                    asyncio.create_task(semaphore_a_fetch_contract_data(target_contract))
                    for target_contract
                    in contract_targets
                ]

                fetch_contracts_results = await asyncio.gather(*fetch_contracts_tasks, return_exceptions=True)

                error_count = 0
                for result, target in zip(fetch_contracts_results, contract_targets):
                    if isinstance(result, Exception):
                        error_count += 1
                        # добавим номер контракта (который не удалось скачать)
                        # в список ошибок скачивания для региона
                        region_fetch_failed_contracts.append(target['number'])
                        # исключим из начального списка номер контракта, который не удалось скачать
                        contracts_nums.remove(target['number'])
                        logger.error(f"Failed fetching contract num {target['number']} "
                                     f"for region {target['region_id']} "
                                     f"with exception {type(result)} "
                                     f"{result}")

                    # для всех остальных, где нет ошибок при скачивании контрактов

                if error_count > 0:
                # были ошибки при скачивании контрактов для региона
                # были исключения из contracts_nums
                # - надо сохранить итоговый contracts_nums в соответствующий файл
                    if len(contracts_nums) > 0:
                        # в contracts_nums остались номера контрактов,
                        # которые удалось скачать - сохраним их в файл

                        new_file_name = replace_counts_in_filename(curr_file.name, len(contracts_nums))
                        print(f"old file name: {curr_file.name}")
                        print(f"new file name: {new_file_name}")
                        await self._a_save_data_to_file(
                            contracts_nums,
                            new_file_name,
                            region_dir,
                        )



            ###########
            # если были ошибки скачивания контрактов для региона
            # - region_fetch_failed_contracts
            # - то запишем их в спец файл в директории региона
            if len(region_fetch_failed_contracts) > 0:
                error_file_name = f"failed_contracts_{region_dir.name}.txt"
                await self._a_save_data_to_file(
                    region_fetch_failed_contracts,
                    error_file_name,
                    region_dir,
                )















        # target_regions = await self._a_get_target_span_files_data(target_dir)
        #
        # for target in targets:
        #     logger.info(f"Start getting contract pages for region {target['region_name']} "
        #                 f"(id: {target['region_id']})")
        #
        #     target['per_page_items'] = per_page_items
        #     target['save_dirs'] = [
        #         self.marketplace_config['dwl_stages']['contracts_pages'],
        #         f'{target["date_from"]}_{target["date_to"]}',
        #         f'{target["region_id"]}'
        #     ]
        #
        #     web_loader_config = self.prepare_single_web_loader_config(target)
        #     # pprint(web_loader_config)
        #     res = await self._get_exact_contracts_pages_on_span(target, web_loader_config)
        #
        #     pprint(res)
        #
        #
        #
        # # прочитать директории с ценовыми промежутками
        # # для регионов для текущих дат from_date и to_date
        # found_target_dir = None
        # found_target_files = []
        # targets = []
        #
        # for p in self._walk_dir_tree(target_dir, include_dirs=True):
        #     if p.is_dir() and p.name == f"{self.from_date}_{self.to_date}":
        #         found_target_dir = p
        #
        #         for file_obj in self._walk_dir_tree(found_target_dir):
        #             found_target_files.append(file_obj)
        #
        # if len(found_target_files) == 0:
        #     #  файлов для обработки не нашлось - останов
        #     raise RuntimeError("Nothing to do (no files)... Exiting...")
        #
        # tasks = [asyncio.create_task(self._read_one_file(path)) for path in found_target_files]
        #
        # results = await asyncio.gather(*tasks)
        #
        # for result, file_obj in zip(results, found_target_files):
        #     # print(f"Read data: {result}")
        #     result = ast.literal_eval(result)
        #     region_id = file_obj.name.split("_")[0]
        #     region_name = file_obj.name.split("_")[1]
        #
        #     targets.append({
        #         "region_id": region_id,
        #         "region_name": region_name,
        #         "file_name": file_obj.name,
        #         "file": file_obj,
        #         "data": list(result),
        #         "length": len(result),
        #         "date_from": self.from_date,
        #         "date_to": self.to_date,
        #         "per_page_items": self.per_page_items,
        #     })
        #
        # return targets



    # @staticmethod
    # async def _a_fetch_page(
    #     config: WebLoaderConfig,
    #     page: int | None = None,
    #     price_from: int | None = None,
    #     price_to: int | None = None,
    # ) -> URLResult:
    #
    #     page_loader = AiohttpDlTransport(config)
    #     set_param = page_loader.urls[0].set_query_params
    #
    #     change_params = []  # список параметров ГКД которые надо поменять
    #     if page:
    #         change_params.append(Page(page))
    #     if price_from:
    #         change_params.append(MinPrice(price_from))
    #     if price_to:
    #         change_params.append(MaxPrice(price_to))
    #
    #     set_param(*change_params)  # установим новые параметры для запроса
    #
    #     download_results = await page_loader.a_run()
    #
    #     logger.info(
    #         f"HTTP Status {download_results[0].url_request.status_code} for "
    #         # f"params: {change_params} . URL {download_results[0].url_request.result_url}"
    #         f"params: {change_params}"
    #     )
    #
    #     return download_results[0]

    @staticmethod
    async def _a_fetch_page(
            config: WebLoaderConfig,
            params: list[QueryParam],
    ) -> URLResult:
        first = 0

        page_loader = AiohttpDlTransport(config)

        # ссылка на функцию установки параметров url
        set_param = page_loader.urls[first].set_query_params

        # список параметров ГКД которые надо поменять
        for param in params:
            if not isinstance(param, QueryParam):
                err_msg = f"param needs to be {type(QueryParam)}, not {type(param)}"
                logger.error(err_msg)
                raise TypeError(err_msg)

        set_param(*params)  # установим новые параметры для запроса

        download_results = await page_loader.a_run()

        logger.debug(
            f"HTTP Status {download_results[first].url_request.status_code} for "
            f"params: {params} for URL: {page_loader.urls[first]}"
        )

        return download_results[first]

