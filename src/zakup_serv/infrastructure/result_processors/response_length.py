import asyncio
import time

from zakup_serv.infrastructure.result_processors.base import DataProcessorInterface
from zakup_serv.domain.actual_contracts.urls import URLRequest, URLResult


class ResponseLength(DataProcessorInterface):
    # для тестовых целей - проверка процессинга результатов запросов

    async def a_process_it(self, result_obj: URLResult) -> URLResult:
        inner_result_obj = result_obj
        print(f"длина {len(inner_result_obj.request_result) or 0}")
        return inner_result_obj

    def process_it(self, result_obj: URLResult) -> URLResult:
        inner_result_obj = result_obj
        time.sleep(1)
        print(f"длина {len(inner_result_obj.request_result) or 0}")
        return inner_result_obj

