import asyncio
from typing import Callable

import aiohttp

from zakup_serv.domain.actual_contracts.urls import URL
from zakup_serv.infrastructure.CustomExceptions import NoNewContractsException, NoDataLoaded
from zakup_serv.transport.base import WebLoaderConfig


class AiohttpDlTransport:
    def __init__(self, config: WebLoaderConfig):

        self.urls = config.urls
        self.http_method = config.http_method
        self.concurrent_connections = config.concurrent_connections
        self.headers = config.headers
        self.fetch_page_timeout = config.fetch_page_timeout
        self.check_ssl = config.check_ssl
        self.callback_on_result = config.callback_on_result


    async def _download(self, session, url: URL):
        # возвратит html страницы
        _download_result = None

        if self.http_method == 'GET':
            async with session.get(url.result_url, timeout=self.fetch_page_timeout) as response:
                response.raise_for_status()
                page_text = await response.text()
                _download_result = page_text
        elif self.http_method == 'POST':
            async with session.post(url.result_url, timeout=self.fetch_page_timeout) as response:
                response.raise_for_status()
                page_text = await response.text()
                _download_result = page_text
        else:
            raise NotImplementedError(f"{self.http_method} не поддерживается в {self.__class__.__name__}")

        # Если задан обработчик результата, то выполним его на полученном ответе
        if self.callback_on_result and isinstance(self.callback_on_result, Callable):
            await self.callback_on_result(url.filename, _download_result)

        return _download_result


    async def _worker(self, url: URL, session, semaphore):
        async with semaphore:
            try:
                response_data = await self._download(session, url)

                if response_data:
                    return response_data
                else:
                    raise NoDataLoaded

            except Exception as e:
                print(f"Ошибка при обработке URL {url.result_url}: {e}")
                raise


    async def fetch_pages(self):
        semaphore = asyncio.Semaphore(self.concurrent_connections)
        connector = aiohttp.TCPConnector(ssl=self.check_ssl)

        async with aiohttp.ClientSession(headers=self.headers, connector=connector) as session:
            tasks = [asyncio.create_task(self._worker(url, session, semaphore)) for url in self.urls]

            try:
                results = await asyncio.gather(*tasks, return_exceptions=True)
                ok, errors = {}, {}
                for url, res in zip(self.urls, results):
                    #print(res)

                    if isinstance(res, Exception):
                        errors[url] = repr(res)
                    else:
                        ok = res

                return ok, errors

            except Exception as e:
                print(f"Обнаружено исключение: {e}")
                # Отмена всех задач
                for task in tasks:
                    task.cancel()
                # Дожидаемся завершения отменённых задач
                await asyncio.gather(*tasks, return_exceptions=True)
                print("Все задачи остановлены из-за исключения.")
                raise  # Пробрасываем исключение дальше
