import re
from bs4 import BeautifulSoup
from zakup_serv.infrastructure.urls import URLResult
from zakup_serv.infrastructure.result_processors.base import DataProcessorInterface
from zakup_serv.infrastructure.result_processors.decorators import net_stat_info



class TenderNumsExtractor(DataProcessorInterface):
    # для тестовых целей - проверка процессинга результатов запросов

    @staticmethod
    @net_stat_info()
    def get_tenders(result_obj: URLResult) -> list:
        # вернёт [(номер, ссылка), ...] или []

        soup = BeautifulSoup(result_obj.request_result, "lxml")

        tenders_blocs = soup.find_all(
            "div", class_="registry-entry__header-mid__number"
        )
        tenders_links = [
            tender.find("a").get("href").strip() for tender in tenders_blocs
        ]
        tender_nums = [
            (re.search(r"regNumber=(\d+)", link).group(1), link)
            for link
            in tenders_links
        ]

        if not tender_nums or len(tender_nums) == 0:
            return []

        # вернёт [(номер, ссылка), ...] или []
        return tender_nums


    async def a_process_it(self, result_obj: URLResult) -> URLResult:
        raise NotImplementedError()
        # inner_result_obj = result_obj
        #
        # soup = BeautifulSoup(inner_result_obj.request_result, "lxml")
        #
        # contracts_blocs = soup.find_all(
        #     "div", class_="registry-entry__header-mid__number"
        # )
        # contract_links = [
        #     contract.find("a").get("href").strip() for contract in contracts_blocs
        # ]
        #
        # # вернёт [(номер, ссылка), ...]
        # contract_nums = [
        #     (re.search(r"regNumber=(\d+)", link).group(1), link)
        #     for link
        #     in contract_links
        # ]
        #
        # # print(len(contracts_blocs))
        #
        # # добавим только уникальные ссылки
        # if not contract_nums or len(contract_nums) == 0:
        #     raise NoNewContractsException(f"На странице не найдено контрактов")
        #
        # # new_contract_nums = [item for item in contract_nums if item not in CONTRACT_NUM_GLOBAL]
        # new_contract_nums = [item for item in contract_nums]
        # if len(new_contract_nums) == 0:
        #     raise NoNewContractsException(f"На странице не найдено новых контрактов")
        #
        # print(f"На странице найдено {len(new_contract_nums)} контрактов")
        #
        #
        #
        # return inner_result_obj

    def process_it(self, result_obj: URLResult) -> URLResult:
        raise NotImplementedError()
        # inner_result_obj = result_obj
        #
        # soup = BeautifulSoup(inner_result_obj.request_result, "lxml")
        #
        # contracts_blocs = soup.find_all(
        #     "div", class_="registry-entry__header-mid__number"
        # )
        # contract_links = [
        #     contract.find("a").get("href").strip() for contract in contracts_blocs
        # ]
        # contract_nums = [
        #     re.search(r"reestrNumber=(\d+)", link).group(1) for link in contract_links
        # ]
        #
        # # print(len(contracts_blocs))
        #
        # # добавим только уникальные ссылки
        # if not contract_nums or len(contract_nums) == 0:
        #     raise NoNewContractsException("На странице не найдено контрактов")
        #
        # # new_contract_nums = [item for item in contract_nums if item not in CONTRACT_NUM_GLOBAL]
        # new_contract_nums = [item for item in contract_nums]
        # if len(new_contract_nums) == 0:
        #     raise NoNewContractsException("На странице не найдено новых контрактов")
        #
        # print(f"На странице найдено {len(new_contract_nums)} контрактов")
        #
        # return inner_result_obj
