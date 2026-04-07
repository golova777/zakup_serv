import asyncio
import time
import aiohttp
from bs4 import BeautifulSoup
from string import Template
import re
import os
from functools import wraps



class AiohttpDlTransport:
    def __init__(
            self,
            url: str,
            http_method: str = "GET",
            concurent_connections: int | None = None,
            headers: dict | None = None,
            fetch_page_timeout: int = 10,

            ):
        ...

    async def fetch_page(self, session, url):
        async with session.get(url, timeout=10) as response:
            response.raise_for_status()
            page_test = await response.text()
            return page_test


    async def worker(self, url, session, semaphore):
        async with semaphore:
            try:
                html = await self.fetch_page(session, url[1])
                contracts_nums_list = await extract_contract_numbers(html, url[0])
                # contracts_nums_list = "dumb"
                print("hit page...")
                result = {
                    "url": url[1],
                    "page": url[0],
                    "contracts_nums": contracts_nums_list
                }
                # print(result)
                if len(contracts_nums_list) == 0:
                    raise NoContractsException(f"На странице {url[0]} не найдено новых контрактов")
                return result

            except Exception as e:
                print(f"Ошибка при обработке URL {url}: {e}")
                raise
