import asyncio
from collections.abc import Callable
import inspect

import aiohttp

from zakup_serv.domain.actual_contracts.urls import URLRequest, URLResult
from zakup_serv.infrastructure.CustomExceptions import NoDataLoaded
from zakup_serv.transport.base import WebLoaderConfig, BaseWebLoaderConfig


class AiohttpDlTransport(BaseWebLoaderConfig):
    # конструктор полностью заимствуется из базового абстрактного класса

    def _load_config(self, config: WebLoaderConfig) -> None:
        self.urls = config.urls
        self.http_method = config.http_method
        self.concurrent_connections = config.concurrent_connections
        self.headers = config.headers
        self.fetch_page_timeout = config.fetch_page_timeout
        self.check_ssl = config.check_ssl
        self.callback_on_instant_result = config.callback_on_instant_result
        self.callback_on_final_result = config.callback_on_final_result

    async def _async_download(self, session, url: URLRequest):
        # возвратит html страницы
        _download_result = None
        _global_response = None

        if self.http_method == 'GET':
            async with session.get(url.result_url, timeout=self.fetch_page_timeout) as response:
                _global_response = response
                response.raise_for_status()
                url.actual_request = response
                page_text = await response.text()
                _download_result = page_text
        elif self.http_method == 'POST':
            async with session.post(url.result_url, timeout=self.fetch_page_timeout) as response:
                _global_response = response
                response.raise_for_status()
                url.actual_request = response
                page_text = await response.text()
                _download_result = page_text
        else:
            raise NotImplementedError(f"{self.http_method} пока не поддерживается в {self.__class__.__name__}")



        if self.callback_on_instant_result and isinstance(self.callback_on_instant_result, Callable):
            if inspect.iscoroutinefunction(self.callback_on_instant_result):
                # для асинхронного обработчика
                url.callback_on_instant_result = await self.callback_on_instant_result(_download_result, url)
            else:
                # для простого синхронного обработчика
                url.callback_on_instant_result = self.callback_on_instant_result(_download_result, url)


            await self.callback_on_instant_result(url.filename, _download_result)
        #####################################################################################
        #####################################################################################
        # TODO сделать нормальный отдельный обрабьотчик обратных вызовов на результат запроса
        # Если задан обработчик результата, то выполним его на полученном ответе
        if self.callback_on_result and isinstance(self.callback_on_result, Callable):
            await self.callback_on_result(url.filename, _download_result)
        #####################################################################################
        #####################################################################################

        return _download_result

    async def a_process_instant_result(self):
        pass

    def process_instant_result(self):
        pass

    async def a_process_final_result(self):
        pass

    def process_final_result(self):
        pass


    async def __async_worker(self, url: URLRequest, session, semaphore):
        async with semaphore:
            try:
                response_data = await self._async_download(session, url)

                ################################################################
                ################################################################

                if "6" in url.filename:
                    print("страница 6 умышленно выдала ошибку")
                    raise NoDataLoaded("Исключение: страница 6 умышленно выдала ошибку")

                ################################################################
                ################################################################

                if response_data:
                    return response_data
                else:
                    raise NoDataLoaded("ошибка загрузки данных")

            except Exception as e:
                print(f"Ошибка при обработке URL {url.result_url}: {e}")
                raise


    async def async_fetch_pages(self) -> list[URLResult]:
        semaphore = asyncio.Semaphore(self.concurrent_connections)
        connector = aiohttp.TCPConnector(ssl=self.check_ssl)

        async with (aiohttp.ClientSession(headers=self.headers, connector=connector) as session):
            tasks = [asyncio.create_task(self.__async_worker(url, session, semaphore)) for url in self.urls]

            results_list = []  # список результатов запросов (типа URLResult)

            try:
                results = await asyncio.gather(*tasks, return_exceptions=True)

                for url, res in zip(self.urls, results):

                    # результаты работы загрузчика страниц
                    result = URLResult(res)
                    result.set_url_request(url)

                    results_list.append(
                        result
                    )

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
