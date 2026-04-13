import asyncio
from collections.abc import Callable
from concurrent.futures import ProcessPoolExecutor
import inspect

import aiohttp

from zakup_serv.domain.actual_contracts.urls import URLRequest, URLResult
from zakup_serv.infrastructure.CustomExceptions import NoDataLoaded
from zakup_serv.transport.base import WebLoaderConfig, BaseWebLoader


class AiohttpDlTransport(BaseWebLoader):
    # конструктор полностью заимствуется из базового абстрактного класса

    def _load_config(self, config: WebLoaderConfig) -> None:
        self.urls = config.urls
        self.http_method = config.http_method
        self.concurrent_connections = config.concurrent_connections
        self.headers = config.headers
        self.fetch_page_timeout = config.fetch_page_timeout
        self.check_ssl = config.check_ssl
        self.callbacks_list_on_result = config.callbacks_list_on_result


    async def _a_download(self, session, url: URLRequest):
        ''' возврат сырых данных веб страницы (или эндпоинта API)
        в виде текста или байтов, в зависимости от типа данных ответа сервера
        '''

        # TODO нужно обрабатывать ошибки для политики ретраев ()
        # Ретраить только временные ошибки: Timeout, ConnectionReset, 503, 502, 429;
        # не ретраить 400/401/403/404 и ошибки валидации.
        # TODO как-то определять - нужно ли ретраить или нет.
        #  и пробрасывать это в блок ретрая решение

        '''
        Ретраить только временные ошибки: Timeout, ConnectionReset, 503, 502, 429; 
        не ретраить 400/401/403/404 и ошибки валидации.
        Использовать exponential backoff + jitter (случайный разброс), чтобы не устроить thundering herd.
        Ограничивать и попытки, и общее время: max_attempts + max_elapsed_seconds.
        Учитывать идемпотентность: GET обычно безопасен для повторов, POST —
         только при idempotency key/гарантиях API.
        Уважать заголовок Retry-After для 429/503 (если есть) — это важнее вашего локального backoff.
        Логировать каждую попытку структурно: URL, attempt, причина, задержка, итог.
        Добавлять “предохранители”: concurrency limit (у вас уже есть semaphore), 
        circuit breaker (если сервер стабильно падает), rate limit.
        
        
        max_attempts: 3–5
        base_delay: 0.3–0.7 сек
        max_delay: 10–30 сек
        jitter: full jitter (random(0, delay))
        request timeout: раздельный connect/read/total, а не один общий
        retry budget: например, не больше 20% запросов в минуту могут быть retry
        '''

        _download_result = None
        _inner_response = None

        if self.http_method == 'GET':
            async with session.get(url.result_url, timeout=self.fetch_page_timeout) as response:
                _inner_response = response
                response.raise_for_status()
                page_text = await response.text()
                _download_result = page_text
        elif self.http_method == 'POST':
            async with session.post(url.result_url, timeout=self.fetch_page_timeout) as response:
                _inner_response = response
                response.raise_for_status()
                page_text = await response.text()
                _download_result = page_text
        else:
            raise NotImplementedError(f"{self.http_method} пока не поддерживается в {self.__class__.__name__}")

        print(_inner_response.status, url.result_url[:50])

        return _download_result


    async def _a_worker(self, url: URLRequest, session, semaphore):

        async with semaphore:
            try:
                response_data = await self._a_download(session, url)


                ################################################################
                #   ПРОВЕРКА НА Ошибки  ###############################################################
                '''
                
                
                if "8" in url.filename:
                    print("страница 8 умышленно выдала ошибку")
                    raise NoDataLoaded("Исключение: страница 6 умышленно выдала ошибку")
                '''
                ################################################################
                ################################################################


                if response_data:
                    return response_data
                else:
                    raise NoDataLoaded("ошибка загрузки данных")

            except Exception as e:
                # TODO нужна политика повторов запросов при ошибках загрузки страниц
                print(f"Ошибка при обработке URL {url.result_url}: {e}")
                raise


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
                tasks = [asyncio.create_task(callback(url_result)) for url_result in self.url_results_list]
                processed_results = await asyncio.gather(*tasks, return_exceptions=True)

                try:
                    for processed, downloaded in zip(processed_results, self.url_results_list):
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
                #with ProcessPoolExecutor() as pool:
                #    return list(pool.map(parse_page, html_pages))

                try:
                    with ProcessPoolExecutor() as pool:
                        finished_processed_results = list(
                            pool.map(
                                callback,
                                self.url_results_list
                            )
                        )

                except Exception as e:
                    #  НЕ ПРОПУСТИМ ОШИБОК ОБРАБОТКИ РЕЗУЛЬТАТОВ СКАЧИВАНИЯ
                    print(f"Ошибка при обработке URL в синхронном обработчике: {e}")
                    raise

                '''
                for url_result in self.url_results_list:
                    try:
                        url_result = callback(url_result)
                        finished_processed_results.append(url_result)
                    except Exception as e:
                        #  НЕ ПРОПУСТИМ ОШИБОК ОБРАБОТКИ РЕЗУЛЬТАТОВ СКАЧИВАНИЯ
                        print(f"Ошибка при обработке URL {url_result.url_request.result_url} в синхронном обработчике: {e}")
                        raise
                '''

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

        async with (aiohttp.ClientSession(headers=self.headers, connector=connector) as session):
            tasks = [asyncio.create_task(self._a_worker(url, session, semaphore)) for url in self.urls]

            results_list = []  # список результатов запросов (типа URLResult)

            try:
                download_results = await asyncio.gather(*tasks, return_exceptions=True)
                # 1. Создадим объекты URLResult
                # для всех результатов совершённых запросов

                # !!! Разбор ошибок запросов должен делать
                # получатель результата скачивания, а не сам загрузчик
                error_count = 0
                for url, res_data in zip(self.urls, download_results):
                    # результаты работы загрузчика страниц
                    # (с включенным объектом запроса URLRequest)
                    if isinstance(res_data, Exception):
                        error_count += 1
                    url_result = URLResult(res_data, url)

                    results_list.append(url_result)

                # выведем статистику выполнения
                print(f"==================="
                     f"Загружено страниц: {len(download_results) - error_count} "
                     f"из {len(download_results)}.\n"
                     f"ошибок: {error_count}")

                #  сохраним список результатов запросов внутри self
                self.url_results_list = results_list

                return results_list

            except Exception as e:
                print(f"Обнаружено исключение: {e}")
                # Отмена всех задач
                for task in tasks:
                    task.cancel()
                # Дожидаемся завершения отменённых задач
                await asyncio.gather(*tasks, return_exceptions=True)
                print("Все задачи остановлены из-за исключения.")
                raise  # Пробрасываем исключение дальше

