import re
from bs4 import BeautifulSoup

from zakup_serv.domain.marketplaces.zakupki_gov_ru.tenders.domain.tender_types import TenderType
from zakup_serv.infrastructure.CustomExceptions import InconsistentDataException
from zakup_serv.infrastructure.urls import URLResult
from zakup_serv.infrastructure.result_processors.base import DataProcessorInterface
from zakup_serv.infrastructure.result_processors.decorators import net_stat_info



class TenderNumsExtractor(DataProcessorInterface):

    @staticmethod
    def extract_tender_type(main_tender_block_soup_obj) -> TenderType:
        # ищем номе фз
        tenders_blocs = main_tender_block_soup_obj.find_all(
            # такой блок должен быть только 1
            "div", class_="registry-entry__header-top__title"
        )
        if len(tenders_blocs) != 1:
            raise InconsistentDataException(message=f"{type(tenders_blocs)} "
                                                    f"should be only one and at least one. "
                                                    f"But got {len(tenders_blocs)}")

        tender_type_title_text = tenders_blocs[0].get_text(strip=True)

        if "44" in tender_type_title_text:
            tender_type = TenderType.FZ44
        elif "223" in tender_type_title_text:
            tender_type = TenderType.FZ223
        elif "615" in tender_type_title_text:
            tender_type = TenderType.PP615
        else:
            raise InconsistentDataException(message=f"Cannot determine "
                                                    f"tender type from text: "
                                                    f"{tender_type_title_text}")

        return tender_type



    @net_stat_info()
    def get_tenders(self, result_obj: URLResult) -> list:
        # вернёт [(номер, ссылка, тип ФЗ), ...] или []

        soup = BeautifulSoup(result_obj.request_result, "lxml")

        tender_main_blocks = soup.find_all(
            "div", class_="search-registry-entry-block"
        )

        tender_data = []

        for main_block in tender_main_blocks:
            tenders_blocs = main_block.find_all(
                "div", class_="registry-entry__header-mid__number"
            )
            if len(tenders_blocs) != 1:
                raise InconsistentDataException(message=f"{type(tenders_blocs)} "
                                                        f"should be only one and at least one. "
                                                        f"But got {len(tenders_blocs)}")

            tenders_link = tenders_blocs[0].find("a").get("href").strip()
            tender_number = re.search(r"regNumber=(\d+)", tenders_link).group(1)
            tender_type = TenderNumsExtractor.extract_tender_type(main_block)

            # наполним результирующий список
            tender_data.append((tender_number, tenders_link, tender_type))

        # вернёт [(номер, ссылка, тип ФЗ), ...] или []
        return tender_data


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
