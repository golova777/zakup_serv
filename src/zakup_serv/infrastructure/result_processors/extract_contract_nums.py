import re
from bs4 import BeautifulSoup

from zakup_serv.infrastructure.CustomExceptions import NoNewContractsException
from zakup_serv.infrastructure.result_processors.base import DataProcessorInterface
from zakup_serv.domain.actual_contracts.urls import URLRequest, URLResult


class ContractNumsExtractor(DataProcessorInterface):
    # для тестовых целей - проверка процессинга результатов запросов

    async def a_process_it(self, result_obj: URLResult) -> URLResult:
        inner_result_obj = result_obj

        soup = BeautifulSoup(inner_result_obj.request_result, "lxml")

        contracts_blocs = soup.find_all(
            "div", class_="registry-entry__header-mid__number"
        )
        contract_links = [
            contract.find("a").get("href").strip() for contract in contracts_blocs
        ]
        contract_nums = [
            re.search(r"reestrNumber=(\d+)", link).group(1) for link in contract_links
        ]

        # print(len(contracts_blocs))

        # добавим только уникальные ссылки
        if not contract_nums or len(contract_nums) == 0:
            raise NoNewContractsException(f"На странице не найдено контрактов")

        # new_contract_nums = [item for item in contract_nums if item not in CONTRACT_NUM_GLOBAL]
        new_contract_nums = [item for item in contract_nums]
        if len(new_contract_nums) == 0:
            raise NoNewContractsException(f"На странице не найдено новых контрактов")

        print(f"На странице найдено {len(new_contract_nums)} контрактов")

        """
        #CONTRACT_NUM_GLOBAL.update(new_contract_nums)

        # тестовая запись содержимого страницы в файл
        save_dir = "downloaded"

        os.makedirs(save_dir, exist_ok=True)
        file_path = os.path.join(save_dir, f"page_{page_num}.html")

        with open(file_path, "w", encoding="utf-8") as f:
            f.write(soup.prettify())
        """

        return inner_result_obj

    def process_it(self, result_obj: URLResult) -> URLResult:
        inner_result_obj = result_obj

        soup = BeautifulSoup(inner_result_obj.request_result, "lxml")

        contracts_blocs = soup.find_all(
            "div", class_="registry-entry__header-mid__number"
        )
        contract_links = [
            contract.find("a").get("href").strip() for contract in contracts_blocs
        ]
        contract_nums = [
            re.search(r"reestrNumber=(\d+)", link).group(1) for link in contract_links
        ]

        # print(len(contracts_blocs))

        # добавим только уникальные ссылки
        if not contract_nums or len(contract_nums) == 0:
            raise NoNewContractsException("На странице не найдено контрактов")

        # new_contract_nums = [item for item in contract_nums if item not in CONTRACT_NUM_GLOBAL]
        new_contract_nums = [item for item in contract_nums]
        if len(new_contract_nums) == 0:
            raise NoNewContractsException("На странице не найдено новых контрактов")

        print(f"На странице найдено {len(new_contract_nums)} контрактов")

        return inner_result_obj
