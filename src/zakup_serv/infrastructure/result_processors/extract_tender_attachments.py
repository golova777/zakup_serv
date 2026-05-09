import re
from pprint import pprint

from bs4 import BeautifulSoup
from typing import Tuple

from zakup_serv.domain.marketplaces.zakupki_gov_ru.tenders.domain.attachment_file import AttachedFile
from zakup_serv.domain.marketplaces.zakupki_gov_ru.tenders.domain.tender_types import TenderType
from zakup_serv.infrastructure.CustomExceptions import InconsistentDataException
from zakup_serv.infrastructure.urls import URLResult
from zakup_serv.infrastructure.result_processors.base import DataProcessorInterface
from zakup_serv.infrastructure.result_processors.decorators import net_stat_info
from urllib.parse import urlparse, parse_qs, unquote_plus



class TenderAttachmentsExtractor(DataProcessorInterface):

    @staticmethod
    def split_filename_simple(fname: str) -> Tuple[str, str]:
        """
        Возвращает (base_name, extension) для имени файла (без пути).
        extension возвращается без ведущей точки, или "" если расширения нет.
        """
        if not fname:
            return ("", "")

        # скрытые файлы типа ".bashrc" — считаем без расширения
        if fname.startswith(".") and fname.count(".") == 1:
            return (fname, "")

        # несколько часто встречающихся multi-расширений
        multi = ("tar.gz", "tar.bz2", "tar.xz", "min.js")
        lname = fname.lower()
        for ext in sorted(multi, key=len, reverse=True):
            if lname.endswith("." + ext):
                cut = len(fname) - (len(ext) + 1)
                return (fname[:cut], ext)

        # по умолчанию — берём всё до последней точки
        base, sep, ext = fname.rpartition(".")
        if sep == "":
            return (fname, "")
        if base == "":
            return (fname, "")  # случай вроде ".env" уже покрыт, но на всякий
        return (base, ext)


    @staticmethod
    def extract_uid(url: str) -> str | None:
        parsed = urlparse(url)
        qs = parse_qs(parsed.query)  # возвращает dict: { 'uid': ['value'], ... }
        uid_list = qs.get('uid')
        if not uid_list:
            return None
        # decode percent-encoding (если есть)
        return unquote_plus(uid_list[0])


    @net_stat_info()
    def get_attachments(self, result_obj: URLResult) -> list[AttachedFile]:
        soup = BeautifulSoup(result_obj.request_result, "lxml")

        attachments = []

        attachment_block = soup.find_all(
            "div", class_="attachment"
        )

        for block in attachment_block:
            span = block.find("span", class_="section__value")
            a = span.find("a")

            attachment = AttachedFile(
                name = self.split_filename_simple(a.get("title").strip())[0], # фактическое имя файла при загрузке
                uid = self.extract_uid(a.get("href").strip()),
                extension = self.split_filename_simple(a.get("title").strip())[1],  # расширение
                full_name = a.get("title").strip(),  # name.extension
                title = a.get_text(strip=True),  # официальное название в блоке вложений в закупке
                link = a.get("href").strip(),
                full_name_with_uid = f"{self.extract_uid(a.get("href").strip())}_{a.get("title").strip()}",
                content=None,
            )
            attachments.append(attachment)
            # pprint(attachment)

        return attachments


        #
        # tender_data = []
        #
        # for main_block in tender_main_blocks:
        #     tenders_blocs = main_block.find_all(
        #         "div", class_="registry-entry__header-mid__number"
        #     )
        #     if len(tenders_blocs) != 1:
        #         raise InconsistentDataException(message=f"{type(tenders_blocs)} "
        #                                                 f"should be only one and at least one. "
        #                                                 f"But got {len(tenders_blocs)}")
        #
        #     tenders_link = tenders_blocs[0].find("a").get("href").strip()
        #     tender_number = re.search(r"regNumber=(\d+)", tenders_link).group(1)
        #     tender_type = TenderNumsExtractor.extract_tender_type(main_block)
        #
        #     # наполним результирующий список
        #     tender_data.append((tender_number, tenders_link, tender_type))
        #
        # # вернёт [(номер, ссылка, тип ФЗ), ...] или []
        # return tender_data


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
