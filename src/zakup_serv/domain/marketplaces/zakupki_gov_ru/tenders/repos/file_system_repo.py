import os
from pathlib import Path
from typing import Iterator

from zakup_serv.domain.marketplaces.zakupki_gov_ru.tenders.domain.tender import Tender
from zakup_serv.domain.marketplaces.zakupki_gov_ru.tenders.repos.base import BaseTenderRepository


class FileSystemTenderRepo(BaseTenderRepository):

    def add_new_tenders(
            self,
            tenders: Tender | list[Tender]
    ) -> int:
        # добавляет только новые тендеры,
        # возвратит число добавленных новых
        pass

    def is_new_tender_num(self, tender: Tender) -> bool:
        # проверка: true если tender_number нет в репозитории, иначе false
        return True

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
