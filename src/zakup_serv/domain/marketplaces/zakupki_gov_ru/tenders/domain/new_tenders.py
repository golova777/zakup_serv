import asyncio
import logging
import os
import ast
import re
from datetime import date
from pathlib import Path
from pprint import pprint
from typing import Callable, Any, Iterator

import aiofiles
import aiohttp
from bs4 import BeautifulSoup
from copy import deepcopy

from zakup_serv.domain.marketplaces.zakupki_gov_ru.tenders.domain.attachment_file import AttachedFile
from zakup_serv.domain.marketplaces.zakupki_gov_ru.tenders.domain.tender import Tender
from zakup_serv.domain.marketplaces.zakupki_gov_ru.tenders.domain.tender_types import TenderType
from zakup_serv.domain.marketplaces.zakupki_gov_ru.tenders.query_parameters.base import QueryParam
from zakup_serv.domain.marketplaces.zakupki_gov_ru.tenders.query_parameters.dates import StartDate
from zakup_serv.domain.marketplaces.zakupki_gov_ru.tenders.query_parameters.pages import PerPage, Page
from zakup_serv.domain.marketplaces.zakupki_gov_ru.tenders.query_parameters.prices import TenderMinPrice, TenderMaxPrice
from zakup_serv.domain.marketplaces.zakupki_gov_ru.tenders.query_parameters.regions import Regions, Region
from zakup_serv.domain.marketplaces.zakupki_gov_ru.tenders.query_parameters.tender_number import TenderNumber
from zakup_serv.domain.marketplaces.zakupki_gov_ru.tenders.repos.base import BaseTenderRepository
from zakup_serv.domain.marketplaces.zakupki_gov_ru.tenders.tender_config import TENDER_MARKETPLACE_INFO
from zakup_serv.infrastructure.CustomExceptions import InconsistentDataException
from zakup_serv.infrastructure.result_processors.decorators import net_stat_info
from zakup_serv.infrastructure.result_processors.extract_tender_attachments import TenderAttachmentsExtractor
from zakup_serv.infrastructure.result_processors.extract_tender_nums import TenderNumsExtractor
from zakup_serv.infrastructure.result_processors.save_on_disk import SaveAnyOnDisk
from zakup_serv.infrastructure.urls import URLRequest, URLResult
from zakup_serv.transport.aiohttp_dl import AiohttpDlTransport
from zakup_serv.transport.base import WebLoaderConfig


# Подключим логирование
logger = logging.getLogger(__name__)



class FzNewTenders:
    def __init__(
        self,
        regions: dict[str, str] = None,
        from_date: str = None,
        # to_date: str = None,
        per_page_items: int | None = None,
        callbacks_on_result: list[Callable] | None = None,
        marketplace_config: dict = TENDER_MARKETPLACE_INFO["EIS"],
        repository: BaseTenderRepository | None = None,
    ):
        # конфиг площадки
        self.marketplace_config = marketplace_config

        self.regions: dict[str, str] = (
            regions if regions else self.marketplace_config["regions"]
        )
        # self.from_date: str = (
        #     from_date
        #     if from_date
        #     else self.marketplace_config["fallback_dates"]["from"]
        # )
        # self.to_date: str = (
        #     to_date if to_date else self.marketplace_config["fallback_dates"]["to"]
        # )
        self.per_page_items: int = (
            per_page_items
            if per_page_items
            else self.marketplace_config["default_per_page_items"]
        )
        self.callbacks_on_result: list[Callable] = (
            callbacks_on_result if callbacks_on_result else []
        )
        # репозиторий хранения
        self.repository = repository if repository else self.marketplace_config["default_repository"]

        # Конфиги для каждого Региона+Диапазон дат
        # self.web_loader_configs: list[WebLoaderConfig] = (
        #     self.prepare_web_loader_configs()
        # )

    @staticmethod
    def _get_tender_fetch_data_loader_config(
            target: Tender,
            link: str | None = None,
    ) -> WebLoaderConfig:

        url = URLRequest(link)
        url.set_query_params(TenderNumber(target.number),)

        web_config = WebLoaderConfig(
            [
                url,
            ],
        )
        return web_config


    def _get_tender_web_config(self, target: dict) -> WebLoaderConfig:

        url = URLRequest(self.marketplace_config["base_url"])

        url.set_query_params(
            Region(region_name=target["region_name"], region_id=target["region_id"]),
            StartDate(target['date_from']),
            # EndDate(target['date_to']),
            PerPage(target['per_page_items']),
            Page(self.marketplace_config["default_page_num"]),
        )
        url.region_id = target["region_id"]
        url.date_from = target['date_from']
        url.region_name = target['region_name']

        # установим иерархию сохранения файлов

        dir1 = "tenders"
        dir2 = target['date_from']
        dir3 = "_".join([target['region_id'], target['region_name']])
        url.save_directories.extend([dir1, dir2, dir3])

        web_config = WebLoaderConfig(
            [
                url,
            ],
        )

        return web_config


    # def prepare_web_loader_configs(self) -> list[WebLoaderConfig]:
    #
    #     regions = Regions(self.regions).regions
    #
    #     configs = []
    #
    #     for region in regions:
    #         url = URLRequest(self.marketplace_config["base_url"])
    #
    #         url.set_query_params(
    #             region,
    #             StartDate(self.from_date),
    #             EndDate(self.to_date),
    #             MinPrice(self.marketplace_config["price"][0]),
    #             MaxPrice(self.marketplace_config["price"][1]),
    #             PerPage(self.per_page_items),
    #             Page(1),
    #         )
    #
    #         # установим иерархию сохранения файлов
    #         dir1 = region.region_name
    #         dir2 = "_".join([self.from_date, self.to_date])
    #         url.save_directories.extend([dir1, dir2])
    #
    #         web_config = WebLoaderConfig(
    #             [
    #                 url,
    #             ],
    #             callbacks_list_on_result=self.callbacks_on_result,
    #         )
    #
    #         configs.append(web_config)
    #
    #     return configs


    # @net_stat_info()
    # async def a_get_current_region_price_spans(self, config: WebLoaderConfig) -> list:
    #
    #     # список диапазонов цен, где будем дробить диапазон
    #     # и после переносить из него подходящие диапазогны
    #     init_prices_spans = [list(self.marketplace_config["price"])]
    #     # результирующий список диапазонов цен, которые подходят по количеству контрактов
    #     result_prices_spans = []
    #     # максимально допустимое число контрактов на ценовой диапазон для того, чтобы его не дробить
    #     max_span_contracts = self.marketplace_config["max_span_contracts"]
    #
    #     logger.info(
    #         f"Start search price spans for region "
    #         f"{config.urls[0].region_name}[id={config.urls[0].region_id}]"
    #     )
    #     while len(init_prices_spans) > 0:
    #         # print(result_prices_spans)
    #         # 1.  получить страницы для извлечения
    #         # количества контрактов для каждого диапазона цен
    #         tasks = [
    #             asyncio.create_task(
    #                 self._a_fetch_page(
    #                     deepcopy(config),
    #                     [
    #                         MinPrice(span[0]),
    #                         MaxPrice(span[1])
    #                     ],
    #                 )
    #             )
    #             for span in init_prices_spans
    #         ]
    #
    #         pass
    #         span_results_pages = await asyncio.gather(*tasks, return_exceptions=True)
    #         logger.info(
    #             f"Fetched {len(span_results_pages)} URLS for price spans for region "
    #             f"{config.urls[0].region_name}[id={config.urls[0].region_id}]"
    #         )
    #
    #         # TODO а стоит ли их прсто отсевать если пришло исключение????
    #         #  там ведь дланные могут быть всё равно
    #         # 2. отсеять интервалы цены для которых вместо страницы пришло исключение
    #         temp_price_spans = []
    #         temp_price_spans_pages = []
    #         temp_price_spans_data = []
    #         temp_price_spans_and_num_contracts = {}
    #         for span, span_page in zip(init_prices_spans, span_results_pages):
    #             if isinstance(span_page.request_result, Exception):
    #                 logger.warning(
    #                     f"ERROR: for region {config.urls[0].region_name} "
    #                     f"(code:{config.urls[0].region_id}) "
    #                     f"span ({str(span)}) got exception [{type(span_page)}]"
    #                 )
    #                 continue
    #             # logger.info(f"for region {config.urls[0].region_name} "
    #             #                f"(code:{config.urls[0].region_id}) "
    #             #                f"span ({str(span)}) URL {span_page.url_request.result_url} ")
    #             temp_price_spans.append(span)
    #             temp_price_spans_pages.append(
    #                 span_page.request_result
    #             )  # сохраняем только контент страниц
    #             temp_price_spans_data.append(
    #                 span_page
    #             )
    #
    #         # 3. получим количество контрактов для каждого диапазона цен,
    #         # для которых успешно получили страницу
    #         with ProcessPoolExecutor() as pool:
    #             contracts_counts = list(
    #                 pool.map(self._get_total_contracts, temp_price_spans_pages)
    #             )
    #
    #         # 4. обработка диапазонов цен в зависимости от количества контрактов в них
    #         for span, total_contracts, url_result in zip(temp_price_spans, contracts_counts, temp_price_spans_data):
    #
    #             region_name = config.urls[0].region_name
    #             region_id = config.urls[0].region_id
    #             print(
    #                 f"For {region_name} (code={region_id}) "
    #                 f"span ({str(span)}) got {total_contracts} contracts "
    #                 # f"URL: {url_result.url_request.result_url if url_result.url_request else 'N/A'}"
    #             )
    #
    #             if total_contracts == 0:
    #                 # В этом диапазоне контрактов нет - удалим его из начального списка
    #                 init_prices_spans.remove(span)
    #                 continue
    #
    #             if total_contracts < max_span_contracts > 0:
    #                 # Этот диапазон цен дробить не надо - переносим его в result_prices_spans
    #                 result_prices_spans.append(span)  # добавим в результат
    #                 init_prices_spans.remove(span)  # удалим из начального списка
    #                 temp_price_spans_and_num_contracts[total_contracts] = span
    #             else:
    #                 # Этот диапазон цен надо дробить -
    #                 # разделим его пополам и добавим обе половины обратно в init_prices_spans
    #                 mid_price = (span[0] + span[1]) // 2
    #                 new_span1 = [span[0], mid_price]
    #                 new_span2 = [mid_price + 1, span[1]]
    #                 init_prices_spans.append(new_span1)
    #                 init_prices_spans.append(new_span2)
    #                 init_prices_spans.remove(span)  # удалим из начального списка
    #
    #     logger.info(
    #         f"Price_spans for region {config.urls[0].region_name}[id={config.urls[0].region_id}] "
    #         f"got results: \n{result_prices_spans}"
    #     )
    #
    #     # запишем в файл
    #     region_id = config.urls[0].region_id
    #     region_name = config.urls[0].region_name
    #     date_from = config.urls[0].date_from
    #     date_to = config.urls[0].date_to
    #     filename = f"{region_id}_{region_name}.txt"
    #     await self._a_save_data_to_file(
    #         # TODO вместо result_prices_spans нужно сделать вызов как на следующей строке
    #         # self._normalize_price_spans(temp_price_spans_and_num_contracts),
    #         result_prices_spans,
    #         filename,
    #         folders=[
    #             self.marketplace_config['dwl_stages']['price_spans'],
    #             f"{self.from_date}_{self.to_date}",
    #         ]
    #     )
    #
    #     return result_prices_spans

    # @staticmethod
    # def _normalize_price_spans(price_spans: list[list]) -> list[list]:
    #     # TODO сделать нормализацию списка промежутков цен.
    #
    #     return price_spans


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


    # @staticmethod
    # async def _read_one_file(path: Path) -> str:
    #     ''' вернёт содержимое файла асинхронно'''
    #     async with aiofiles.open(path, mode="r", encoding="utf-8") as f:
    #         return await f.read()
    #
    #
    # async def _a_get_target_span_files_data(
    #         self,
    #         target_dir: Path
    # ) -> list[dict]:
    #     # прочитать директории с ценовыми промежутками
    #     # для регионов для текущих дат from_date и to_date
    #     found_target_dir = None
    #     found_target_files = []
    #     targets = []
    #
    #     for p in self._walk_dir_tree(target_dir, include_dirs=True):
    #         if p.is_dir() and p.name == f"{self.from_date}_{self.to_date}":
    #             found_target_dir = p
    #
    #             for file_obj in self._walk_dir_tree(found_target_dir):
    #                 found_target_files.append(file_obj)
    #
    #     if len(found_target_files) == 0:
    #         #  файлов для обработки не нашлось - останов
    #         raise RuntimeError("Nothing to do (no files)... Exiting...")
    #
    #     tasks = [asyncio.create_task(self._read_one_file(path)) for path in found_target_files]
    #
    #     results = await asyncio.gather(*tasks)
    #
    #     for result, file_obj in zip(results, found_target_files):
    #         # print(f"Read data: {result}")
    #         result = ast.literal_eval(result)
    #         region_id = file_obj.name.split("_")[0]
    #         region_name = file_obj.name.split("_")[1]
    #
    #         targets.append({
    #             "region_id": region_id,
    #             "region_name": region_name,
    #             "file_name": file_obj.name,
    #             "file": file_obj,
    #             "data": list(result),
    #             "length": len(result),
    #             "date_from": self.from_date,
    #             "date_to": self.to_date,
    #             "per_page_items": self.per_page_items,
    #         })
    #
    #     return targets

    async def _a_iterate_tenders_search_pages(
            self,
            web_config: WebLoaderConfig,
            repository: BaseTenderRepository,
            start_page: int = 1,
            per_page_items: int = 10,
            price_from: int | None = None,
            price_to: int | None = None,
            save_dirs: list[str] | None = None,
    ) -> list[Tender]:

        # Здесь будет идти последовательный перебор страниц
        # с проверкой на наличие закупок
        region_id = web_config.urls[0].region_id
        region_name = web_config.urls[0].region_name
        date_from = web_config.urls[0].date_from

        # здесь не должно быть None
        if not region_id or not region_name or not date_from:
            raise InconsistentDataException(
                "some is None",
                par1=region_id,
                par2=region_name,
                par3=date_from
            )

        max_pages = int(
            self.marketplace_config["db_limit_max_span_contracts"] / per_page_items
        )

        # Хранит объекты Tender()
        # для текущего скачивания на один регион
        tenders = []

        # пройдём по всем доступным страницам выдачи поиска закупок
        for page_number in range(start_page, max_pages+1):
            page = Page(page_number)
            # на случай, если нужно будет отрабатывать закупки по ценовым диапазонам
            price_min = TenderMinPrice(price_from) if price_from else None
            price_max = TenderMaxPrice(price_to) if price_to else None

            url_result = await self._a_fetch_page(
                deepcopy(web_config),
                [
                    # Здесь можно кастомизировать запрос к перечню закупок
                    # дополнительными QueryParam()
                    page,
                    # price_min,
                    # price_max,
                ],
            )
            logger.info(
                f"Fetched tender listing page №{page_number} "
                f"for region {web_config.urls[0].region_id} "
                # f"URL: {url_result.url_request.result_url}"
            )

            # Извлечь номера закупок со страницы
            # вернёт [(номер, ссылка, тип ФЗ), ...] или []
            tenders_list = await asyncio.to_thread(TenderNumsExtractor().get_tenders, url_result)
            # преобразуем в объекты Tender()
            if tenders_list:
                tenders_list = [
                    Tender(
                        number=tender[0],
                        link=tender[1],
                        region_name=region_name,
                        region_id=region_id,
                        publish_date=date_from,
                        tender_type=tender[2],
                    )
                    for tender
                    in tenders_list
                ]

            # ОТБОР ТОЛЬКО СВЕЖИХ ТЕНДЕРОВ - КОТОРЫХ НЕТ В БД
            # TODO сделать в репозитории реальную проверку на новизну тендера.
            #  Сейчас все считаются новыми!!!
            # Отсеем номера тендеров, которые уже есть в репозитории - оставим только новые
            new_tenders_list = [
                tender
                for tender
                in tenders_list
                if repository.is_new_tender_num(tender.number)
            ]

            if len(new_tenders_list) == 0:
                # нет больше тендеров
                # TODO реализовать проверку 1-2 следующих страниц с тендерами - для избыточности
                logger.info(f"No more tenders on page {page_number} "
                            f"for region {web_config.urls[0].region_id} ")
                break
            else:
                # есть тендеры
                tenders.extend(new_tenders_list)


                # сохраним страницу на диск
                # await SaveAnyOnDisk.a_process_it(
                #     url_result.request_result,
                #     f"{region_id}_date_{date_from}_{date_to}_price_{price_from}_{price_to}_page_{page_number}.txt",
                #     folders=save_dirs
                # )

        # сохраним только номера тендеров на диск
        await SaveAnyOnDisk.a_process_it(
            tenders,
            f"{region_id}_date_{date_from}_counts_{len(tenders)}.txt",
            folders=save_dirs
        )

        # вернём [Tender(), ...]
        return tenders


    # async def _get_tenders(
    #         self,
    #         target: dict,
    #         web_config: WebLoaderConfig,
    # ):
    #         total_contracts_list = []
    #
    #         # для каждого ценового диапазона скачиваем страницы пагинации
    #         tasks = [
    #             asyncio.create_task(
    #                 self._a_iterate_tenders_search_pages(
    #                     deepcopy(web_config),
    #                     price_from=span[0],
    #                     price_to=span[1],
    #                     start_page = 1,
    #                     per_page_items = target['per_page_items'],
    #                     save_dirs=target['save_dirs'],
    #                 )
    #             )
    #             for span in target['data']
    #             # for span in [target['data'][3],]
    #         ]
    #
    #         contract_lists = await asyncio.gather(*tasks, return_exceptions=True)
    #
    #         for contracts in contract_lists:
    #             if type(contracts) is list and len(contracts) > 0:
    #                 total_contracts_list.extend(contracts)
    #             else:
    #                 raise RuntimeError(f"ERROR: strange contract list: {type(contracts)} "
    #                                    f"with content {contracts}")
    #
    #         # сохраним список контрактов
    #         # await SaveAnyOnDisk.a_process_it(
    #         #     total_contracts_list,
    #         #     f"{target['region_id']}_contracts_numbers_{len(total_contracts_list)}.txt",
    #         #     folders=target['save_dirs']
    #         #
    #         # )
    #
    #         logger.info(
    #             f"Fetched {len(total_contracts_list)} contract numbers "
    #             f"for contracts pages for region "
    #             f"{target['region_name']} (id: {target['region_id']})"
    #         )
    #
    #         return total_contracts_list


    async def a_get_tenders(
            self,
            per_page_items: int = 10,
            concurrent: int = 1,
            from_date: str = date.today().strftime("%d.%m.%Y"),
    ):
        # будет собирать: [(target, conf), ...]
        targets_confs = []
        # количество одновременно обрабатываемых РЕГИОНОВ!!!
        semaphore = asyncio.Semaphore(concurrent)

        # 0. создадим конфиги для каждого региона
        for region_id, region_name in self.regions.items():
            logger.info(f"Start searching tenders pages for region {region_name} "
                        f"(id: {region_id})")
            target = dict()

            target["date_from"] = from_date
            target["region_id"] = region_id
            target["region_name"] = region_name
            target['per_page_items'] = per_page_items
            target['save_dirs'] = [
                self.marketplace_config['dwl_stages']['tenders_pages'],
                f'{target["date_from"]}',
                f'{target["region_id"]}'
            ]

            web_loader_config = self._get_tender_web_config(target)
            pprint(web_loader_config)
            # res = await self._get_tenders(target, web_loader_config)

            targets_confs.append((target, web_loader_config))

        # 1. выполним конкурентно поиск закупок для N регионов asyncio.gather...
        ##############################################################
        async def semaphore_get_tenders_pages(tender_target, tender_config):
            async with semaphore:
                return await self._a_iterate_tenders_search_pages(
                    web_config=tender_config,
                    repository=self.repository,
                    per_page_items=tender_target['per_page_items'],
                    save_dirs=tender_target['save_dirs'],
                )

        result_new_tenders = []  # хранит объекты Tender() для всех новых тендеров
        try:
            tasks = [
                asyncio.create_task(semaphore_get_tenders_pages(setting[0], setting[1],))
                for setting
                in targets_confs
            ]

            results = await asyncio.gather(*tasks, return_exceptions=True)


            error_count = 0
            for target_config, tenders in zip(targets_confs, results):
                config = target_config[1]

                if isinstance(tenders, Exception):
                    error_count += 1
                    logger.warning(
                        f"ERROR: for region {config.urls[0].region_name} "
                        f"(code:{config.urls[0].region_id}) "
                        f"tender search got exception [{type(tenders)}]"
                        f"exception content: {tenders}"
                    )
                else:
                    result_new_tenders.extend(tenders)

            # логируем статистику выполнения
            logger.info(
                f"Downloaded tender numbers {len(result_new_tenders)}. With Errors: {error_count}"
            )

        except Exception as e:
            logger.exception(e)

        ################
        # сохраним файлы закупок
        ################

        # result_new_tenders
        # все новые тендеры передаём на скачивание и сохранение
        # TODO надо отдельнеый блок semaphore конкурентности организовать
        #  при скачивании, а параметр количества надо передавать изначально
        saved_count = await self.a_fetch_n_save_tenders_data(result_new_tenders, self.repository)



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


    async def a_fetch_n_save_tenders_data(
            self,
            tenders_list: list[Tender],
            repository: BaseTenderRepository,
    ):
        for tender in tenders_list:
            # TODO сделать параллельную обработку несокльких тендеров сразу
            if tender.tender_type == TenderType.FZ44:
                await self.a_fetch_n_save_fz44_tender_data(tender , repository)
            elif tender.tender_type == TenderType.FZ223:
                print("it is 223!!!!!")
            elif tender.tender_type == TenderType.PP615:
                print("it is 615!!!!!")
            else:
                raise Exception(f"Unknown tender type: {tender.tender_type}")


    async def a_get_tenders_pages(
            self,
            concurrent: int = 1,
    ):
        semaphore = asyncio.Semaphore(concurrent)

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
    async def a_fetch_n_save_fz44_tender_data(
            self,
            target_tender: Tender,
            repository: BaseTenderRepository,
    ):
        ###################################################
        # Фаза 1 основные страницы из реестра контрактов
        tender_content = {
            "common_info": {
                "link": "https://zakupki.gov.ru/epz/order/notice/zk20/view/common-info.html?regNumber=",
                "data": None,
                "attachments": list(),
            },
            "documents": {
                "link": "https://zakupki.gov.ru/epz/order/notice/zk20/view/documents.html?regNumber=",
                "data": None,
                "attachments": list(),
            },
            "event_journal": {
                "link": "https://zakupki.gov.ru/epz/order/notice/zk20/view/event-journal.html?regNumber=",
                "data": None,
                "attachments": list(),
            },
        }

        # query параметр номера закупки
        tender_num_param = TenderNumber(target_tender.number)

        try:

            for section_title, section_data in tender_content.items():
                link = section_data["link"]
                config = self._get_tender_fetch_data_loader_config(target_tender, link)
                fetched_section = await self._a_fetch_page(config, [tender_num_param])
                section_data["data"] = fetched_section.request_result
                logger.info(f"Fetched (len={len(fetched_section.request_result)} bytes) section {section_title} "
                            f"for tender {target_tender.number} "
                            f"for region {target_tender.region_name} "
                            f"(region_id: {target_tender.region_id})")

                # проверим наличие файлов вложенных
                tender_attachments = TenderAttachmentsExtractor().get_attachments(fetched_section)
                if tender_attachments:
                    # print(target_tender.link)
                    # section_data["attachments"] = tender_attachments
                    logger.info(f"Found {len(tender_attachments)} attachments in section {section_title} "
                                f"for tender {target_tender.number} "
                                f"for region {target_tender.region_name} "
                                f"(region_id: {target_tender.region_id})")

                    for attachment in tender_attachments:
                        # TODO сделать параллельное скачивание файлов вложений
                        web_config = WebLoaderConfig([URLRequest(attachment.link),],)
                        fetched = await self._a_fetch_page(web_config)
                        fetched_data: bytes = fetched.request_result
                        # attachment.content = fetched_data.decode("utf-8")
                        attachment.content = fetched_data

                        print(
                            f"вложение \"{attachment.full_name}\" "
                            f"для закупки {target_tender.number} "
                            f"имеет размер {len(fetched_data)} bytes")

                    # сохраним вложения в секции
                    section_data["attachments"] = tender_attachments

        except Exception as e:
            logger.exception(e, exc_info=True)
        else:
            # Успешная загрузка файлов и страниц закупки - сохраним данные через репозиторий
            target_tender.content = tender_content

        return None


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
            params: list[QueryParam | None] | None = None,
    ) -> URLResult:
        first = 0

        page_loader = AiohttpDlTransport(config)

        if params:
            # ссылка на функцию установки параметров url
            set_param = page_loader.urls[first].set_query_params
            # список параметров ГКД которые надо поменять
            for param in params:
                if not param:
                    # пропустим те, что None
                    continue
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

