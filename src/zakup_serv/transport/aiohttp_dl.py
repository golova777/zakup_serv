import asyncio
from concurrent.futures import ProcessPoolExecutor
import inspect
from typing import Generator, Callable

import aiohttp
import logging

from zakup_serv.domain.actual_contracts.urls import URLRequest, URLResult
from zakup_serv.infrastructure.CustomExceptions import (
    NoDataLoaded,
    RetriableNetworkError,
    NotRetriableNetworkError,
    ExceededRetryAttemptsError,
)
from zakup_serv.settings import DEFAULT_RETRY_POLICY
from zakup_serv.transport.base import WebLoaderConfig, BaseWebLoader

# Подключим логирование
logger = logging.getLogger(__name__)


class AiohttpDlTransport(BaseWebLoader):
    # конструктор полностью заимствуется из базового абстрактного класса

    def _load_config(self, config: WebLoaderConfig) -> None:
        self.urls = config.urls
        self.http_method = config.http_method
        self.concurrent_connections = config.concurrent_connections
        self.headers = config.headers
        self.fetch_page_timeout = config.fetch_page_timeout
        self.check_ssl = config.check_ssl
        self.proxy = config.proxy
        self.callbacks_list_on_result = config.callbacks_list_on_result

        # БЛОК ОТЛАДКИ
        # генератор последовательности HTTP кодов ответов
        # - для проверки ретраев
        self.fake_http_code_gen: Callable | None = None

    async def _a_download(
        self,
        session,
        url: URLRequest,
        forced_http_status: Generator[int, None, None] | None = None,
    ):
        """возврат сырых данных веб страницы (или эндпоинта API)
        в виде текста или байтов, в зависимости от типа данных ответа сервера
        """

        def save_request_info(url_request: URLRequest, session_result):
            url_request = url_request
            url_request.ok = session_result.ok
            url_request.status_code = session_result.status
            return url_request

        _download_result = None
        _inner_response = None

        try:
            if self.http_method == "GET":
                async with session.get(
                    url.result_url,
                    timeout=self.fetch_page_timeout,
                    proxy=self.proxy,
                ) as response:
                    ####################
                    # ДЛЯ ОТЛАДКИ: опциональная принудительная установка HTTP статусов
                    fake_http_code = (
                        next(forced_http_status, None) if forced_http_status else None
                    )
                    response.status = (
                        fake_http_code if fake_http_code else response.status
                    )
                    ####################

                    _inner_response = response
                    url = save_request_info(url, response)
                    response.raise_for_status()
                    page_text = await response.text()
                    _download_result = page_text
            elif self.http_method == "POST":
                async with session.post(
                    url.result_url,
                    timeout=self.fetch_page_timeout,
                    proxy=self.proxy,
                ) as response:
                    #####################
                    # ДЛЯ ОТЛАДКИ: опциональная принудительная установка HTTP статусов
                    response.status = (
                        forced_http_status if forced_http_status else response.status
                    )
                    ####################

                    _inner_response = response
                    url = save_request_info(url, response)
                    response.raise_for_status()
                    page_text = await response.text()
                    _download_result = page_text
            else:
                raise NotImplementedError(
                    f"{self.http_method} "
                    f"пока не поддерживается "
                    f"в {self.__class__.__name__}"
                )
        except NotImplementedError as e:
            # для http методов, которые ещё не реализованы
            logger.exception(
                f"HTTP method {self.http_method} "
                f"not supported in {self.__class__.__name__}",
                exc_info=True,
            )
            raise e
        except Exception as e:
            # Возникла ошибка во время загрузки страницы
            if _inner_response.status in DEFAULT_RETRY_POLICY["status_forcelist"]:
                # данную ошибку загрузки можно ретраить
                logger.exception(
                    f"Failed download but can RETRY!" f"URL {url.result_url}",
                    exc_info=True,
                )
                raise RetriableNetworkError(e)
            else:
                # данную ошибку загрузки нельзя ретрайить
                logger.exception(
                    f"Final Fail! Can't RETRY. Exception while downloading "
                    f"URL {url.result_url}",
                    exc_info=True,
                )
                raise NotRetriableNetworkError(e)
        else:
            # страница загружена нормально
            logger.info(
                f"Статус: {_inner_response.status}, "
                f"len: {len(_download_result) if _download_result else 0}"
            )
            logger.debug(f"Статус: {_inner_response.status}, " f"url: {url.result_url}")

        return _download_result

    async def _a_worker(self, url: URLRequest, session, semaphore):

        async with semaphore:
            # ОТЛАДКА: применим генератор фейковых HTTP кодов ответов #####################
            # для проверки работы механизма ретраев при различных ошибках загрузки ########
            fake_http_code = (
                self.fake_http_code_gen() if self.fake_http_code_gen else None
            )
            ###############################################################################

            try:
                for attempt in range(1, DEFAULT_RETRY_POLICY["retries"] + 1):
                    # Поппытки скачать содержимое страницы
                    try:
                        url.attempt = attempt

                        response_data = await self._a_download(
                            session, url, forced_http_status=fake_http_code
                        )

                    except RetriableNetworkError as e:
                        logger.warning(
                            f"Failed #{attempt} attempt to download data. "
                            f"Exception {type(e)}, "
                            f"Request status code {url.status_code}"
                            f"URL {url.result_url}"
                        )
                        # Прогрессивное ожидание перед следующей попыткой скачать страницу
                        delay_func = DEFAULT_RETRY_POLICY["delay_increase_func"]
                        delay = delay_func(
                            DEFAULT_RETRY_POLICY["backoff_factor"], attempt
                        )
                        await asyncio.sleep(delay)
                        continue  # перейти к следующей попытке

                    except Exception as e:
                        logger.exception(
                            f"Fatally Failed " f"#{attempt} attempt to download data. ",
                            exc_info=True,
                        )
                        # TODO можно ли возврачать исключения иил их надо всё же raise???
                        raise e

                    else:
                        if response_data:
                            # Всё скачали - выходи
                            logger.debug(
                                f"Successfully downloaded: {len(response_data)} chars "
                                f"with URL {url.result_url}"
                            )
                            return response_data
                        else:
                            logger.error(f"No data loaded for URL {url.result_url}")
                            raise NoDataLoaded("ошибка загрузки данных")

                # Все попытки исчерпаны. Следовательно, ExceededRetryAttemptsError
                raise ExceededRetryAttemptsError(
                    f"Can't download URL "
                    f"in {DEFAULT_RETRY_POLICY['retries']} "
                    f"attempts. URL: {url.result_url}"
                )

            except (ExceededRetryAttemptsError, NotRetriableNetworkError) as e:
                # ошибки исчерпания лимита попыток и необрабатываемые сбои скачивания
                if isinstance(e, NotRetriableNetworkError):
                    logger.exception(
                        f"Not retriable error occurred, "
                        f"while retry attempts executed",
                        exc_info=True,
                    )
                if isinstance(e, ExceededRetryAttemptsError):
                    logger.exception(
                        f"Exceeded retry attempts value, "
                        f"while retry attempts executed",
                        exc_info=True,
                    )
                return e

            except (TimeoutError, Exception) as e:
                # ошибка просто запишется в результат скачивания, но программа не остановится
                logger.exception(
                    f"{type(e)} exception occurred," f" while retry attempts executed",
                    exc_info=True,
                )
                return TimeoutError

    async def a_process_results(self) -> list[URLResult]:
        # Обработчики применяются последовательно к набору результатов
        # каждый обработчик принимает на вход ИСХОДНЫЙ набор результатов URLResult

        callbacks = self.callbacks_list_on_result

        # не задано ни одного обработчика
        # - вернём исходные результаты
        if not callbacks:
            print("Выход. Не задано ни одного обработчика результатов скачивания...")
            return self.url_results_list

        for callback in callbacks:

            finished_processed_results = []

            if inspect.iscoroutinefunction(callback):
                #####################################################
                # для асинхронного обработчика
                #####################################################
                tasks = [
                    asyncio.create_task(callback(url_result))
                    for url_result in self.url_results_list
                ]
                processed_results = await asyncio.gather(*tasks, return_exceptions=True)

                try:
                    for processed, downloaded in zip(
                        processed_results, self.url_results_list
                    ):
                        if isinstance(processed, Exception):
                            #  НЕ ПРОПУСТИМ ОШИБОК ОБРАБОТКИ РЕЗУЛЬТАТОВ СКАЧИВАНИЯ
                            raise processed
                        else:
                            finished_processed_results.append(processed)

                    # перезапишем self.url_results_list
                    self.url_results_list = finished_processed_results

                except Exception as e:
                    print(f"Ошибка при обработке URL в асинхронном обработчике: {e}")
                    # отменим незавершившиеся задачи
                    for task in tasks:
                        if not task.done():
                            task.cancel()
                    # Дожидаемся завершения отменённых задач
                    await asyncio.gather(*tasks, return_exceptions=True)
                    raise

            else:
                #####################################################
                # для синхронного обработчика
                #####################################################
                # with ProcessPoolExecutor() as pool:
                #    return list(pool.map(parse_page, html_pages))

                try:
                    with ProcessPoolExecutor() as pool:
                        finished_processed_results = list(
                            pool.map(callback, self.url_results_list)
                        )

                except Exception as e:
                    #  НЕ ПРОПУСТИМ ОШИБОК ОБРАБОТКИ РЕЗУЛЬТАТОВ СКАЧИВАНИЯ
                    print(f"Ошибка при обработке URL в синхронном обработчике: {e}")
                    raise

                """
                for url_result in self.url_results_list:
                    try:
                        url_result = callback(url_result)
                        finished_processed_results.append(url_result)
                    except Exception as e:
                        #  НЕ ПРОПУСТИМ ОШИБОК ОБРАБОТКИ РЕЗУЛЬТАТОВ СКАЧИВАНИЯ
                        print(f"Ошибка при обработке URL {url_result.url_request.result_url} в синхронном обработчике: {e}")
                        raise
                """

                # перезапишем self.url_results_list
                self.url_results_list = finished_processed_results

        return self.url_results_list

    async def a_run(self) -> list[URLResult]:
        await self.async_fetch_pages()
        processed_results = await self.a_process_results()

        return processed_results

    async def async_fetch_pages(self) -> list[URLResult]:
        semaphore = asyncio.Semaphore(self.concurrent_connections)
        connector = aiohttp.TCPConnector(ssl=self.check_ssl)
        # TODO подключить таймауты корректно

        async with aiohttp.ClientSession(
            headers=self.headers, connector=connector
        ) as session:
            logger.debug(
                f"Started aiohttp.ClientSession for {len(self.urls)} "
                f"URLs with concurrency {self.concurrent_connections}"
            )
            tasks = [
                asyncio.create_task(self._a_worker(url, session, semaphore))
                for url in self.urls
            ]

            results_list = []  # список результатов запросов (типа URLResult)

            try:
                download_results = await asyncio.gather(*tasks, return_exceptions=True)
                # download_results = await asyncio.gather(*tasks)
                # 1. Создадим объекты URLResult
                # для всех результатов совершённых запросов

                # !!! Разбор ошибок запросов должен делать
                # получатель результата скачивания, а не сам загрузчик
                error_count = 0
                for url, res_data in zip(self.urls, download_results):
                    # результаты работы загрузчика страниц
                    # (с включенным объектом запроса URLRequest)
                    url_result = URLResult(res_data, url)

                    if isinstance(res_data, Exception):
                        error_count += 1
                        url_result.downloading_raised_exceptions = res_data
                        logger.warning(
                            f"Caught exception [{type(res_data)}] while downloading URL {url.result_url}"
                        )

                    results_list.append(url_result)

                # логируем статистику выполнения
                logger.info(
                    f"Downloaded URLs {len(results_list)}. With Errors: {error_count}"
                )

                #  сохраним список результатов запросов внутри self
                self.url_results_list = results_list

                return results_list

            except Exception as e:
                logger.exception(f"Failed to download pages")
                raise
