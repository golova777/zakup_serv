import logging
import os
from pathlib import Path
from typing import Iterator

from zakup_serv.domain.marketplaces.zakupki_gov_ru.tenders.domain.tender import Tender
from zakup_serv.domain.marketplaces.zakupki_gov_ru.tenders.repos.base import BaseTenderRepository
from zakup_serv.infrastructure.result_processors.save_on_disk import SaveAnyOnDisk
from zakup_serv.settings import SAVERS_DEFAULTS

# from zakup_serv.domain.marketplaces.zakupki_gov_ru.tenders.tender_config import TENDER_MARKETPLACE_INFO

# Подключим логирование
logger = logging.getLogger(__name__)

class FileSystemTenderRepo(BaseTenderRepository):

    def __init__(
            self,
            marketplace_config: dict,
    ) -> None:
        super().__init__(marketplace_config)
        # корневая директория работы с тендерами
        self.base_save_dir = self.marketplace_config["prefix_tender_save_dir"]
        self.tender_data_save_dir = self.marketplace_config["dwl_stages"]["tenders_data"]


    async def add_new_tenders(
            self,
            tenders: Tender | list[Tender]
    ) -> int:
        # добавляет только новые тендеры,
        # возвратит число добавленных новых
        if isinstance(tenders, Tender):
            # обрабатывать будем всегда список
            tenders = [tenders]

        saved_count = 0
        for tender in tenders:
            res = await self._add_new_tender(tender)
            if res:
                saved_count += 1

        return saved_count


    async def _add_new_tender(self, tender) -> bool:
        save_result = False

        save_dirs = [self.base_save_dir]
        save_dirs.append(self.marketplace_config["dwl_stages"]["tenders_data"])
        save_dirs.append(tender.publish_date)
        save_dirs.append(tender.region_id)
        save_dirs.append(tender.number)

        sections = tender.sections_content

        for section_name, section_content in sections.items():
            # TODO доделать сохранение attachments
            section_filename = f"section_{str(section_name)}.txt"
            section_content = section_content["data"]
            section_save_dirs = save_dirs

            try:
                # сохраним страницу на диск
                res = await SaveAnyOnDisk().a_process_it(
                    section_content,
                    section_filename,
                    folders=section_save_dirs,
                )

                if not res:
                    raise RuntimeError(f"Failed to save {section_filename} for tender {tender.number}")
            except Exception as e:
                logger.exception(e, exc_info=True)
                save_result = False
            else:
                save_result = True

        return save_result


    async def is_new_tender_num(self, tender: Tender, **kwargs) -> bool:
        # TODO сделать в репозитории реальную проверку на новизну тендера.
        #  Сейчас все считаются новыми!!!
        # проверка: true если tender_number нет в репозитории, иначе false
        check_path = (
                Path(SAVERS_DEFAULTS["SAVE_FOLDER"])
                / Path(self.base_save_dir)
                / Path(self.tender_data_save_dir)
                / Path(tender.publish_date)
                / Path(tender.region_id)
                / Path(tender.number)
        )
        if check_path.exists() and check_path.is_dir():
            logger.info(f"Tender {tender.   number} already exists in repository. Path: {check_path}")
            return False
        else:
            logger.info(f"NEW Tender {tender.number}. Let's add it")
            return True

    # class Tender:
    #     number: str
    #     link: str
    #     region_name: str
    #     region_id: str
    #     publish_date: str
    #     tender_type: TenderType
    #     sections_content: Any | None = None

    @staticmethod
    def _walk_dir_tree(
            root: str | Path,
            include_dirs: bool = True,
            include_files: bool = False,
            filter_dirs: list[str] | None = None,
    ) -> Iterator[Path]:
        """
        Обходит дерево директорий от `root` вниз.

        :param root: корневая папка
        :param include_dirs: если True, возвращает и папки тоже
        :return: итератор Path-объектов
        """
        root = Path(root)

        for dirpath, dirnames, filenames in os.walk(root):
            current_dir = Path(dirpath)

            if include_dirs:
                for d in dirnames:
                    if filter_dirs:
                        if d in filter_dirs:
                            yield current_dir / d
                    else:
                        yield current_dir / d
            if include_files:
                for f in filenames:
                    yield current_dir / f
