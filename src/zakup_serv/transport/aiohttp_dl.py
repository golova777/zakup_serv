import asyncio
import time
import aiohttp
from bs4 import BeautifulSoup
from string import Template
import re
import os
from functools import wraps


from zakup_serv.settings import DEFAULTS
from zakup_serv.infrastructure.CustomExceptions import NoNewContractsException, NoDataLoaded
from zakup_serv.transport.base import WebLoaderConfig


class AiohttpDlTransport:
    def __init__(
            self,
            config: WebLoaderConfig,
    ):
        self.urls = config.urls
        self.http_method = config.http_method
        self.concurrent_connections = config.concurrent_connections
        self.headers = config.headers
        self.fetch_page_timeout = config.fetch_page_timeout
        self.check_ssl = config.check_ssl
        self.callback_on_result = config.callback_on_result

    async def _download(self, session, url):
        # возвратит html страницы
        if self.http_method == 'GET':
            async with session.get(url, timeout=self.fetch_page_timeout) as response:
                response.raise_for_status()
                page_text = await response.text()
                return page_text
        elif self.http_method == 'POST':
            async with session.post(url, timeout=self.fetch_page_timeout) as response:
                response.raise_for_status()
                page_text = await response.text()
                return page_text
        else:
            raise NotImplementedError(f"{self.http_method} не поддерживается в {self.__class__.__name__}")


    async def worker(self, url, session, semaphore):
        async with semaphore:
            try:
                response_data = await self._download(session, url)

                if response_data:
                    return response_data
                else:
                    raise NoDataLoaded

            except Exception as e:
                print(f"Ошибка при обработке URL {url}: {e}")
                raise



    async def fetch_pages(self, urls):
        semaphore = asyncio.Semaphore(self.concurrent_connections)
        connector = aiohttp.TCPConnector(ssl=self.check_ssl)

        async with aiohttp.ClientSession(headers=self.headers, connector=connector) as session:
            tasks = [asyncio.create_task(self.worker(url, session, semaphore)) for url in urls]

            try:
                results = await asyncio.gather(*tasks, return_exceptions=True)
                ok, errors = {}, {}
                for url, res in zip(urls, results):
                    print(res)

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
