from pathlib import Path
from typing import Any

import aiofiles

from zakup_serv.domain.marketplaces.zakupki_gov_ru.contracts.urls import URLResult
from zakup_serv.infrastructure.result_processors.base import DataProcessorInterface
from zakup_serv.settings import SAVERS_DEFAULTS


class SavePageOnDisk(DataProcessorInterface):
    # Сохранит строковые данные на диск
    def __init__(
        self,
        folder: str = SAVERS_DEFAULTS["SAVE_FOLDER"],
    ):
        self.folder = Path(folder)

    async def a_process_it(
        self,
        result_obj: URLResult,
    ) -> URLResult:

        full_path = self.folder

        if result_obj.url_request and len(result_obj.url_request.save_directories) > 0:
            sub_dirs = result_obj.url_request.save_directories

            # если указано в URLRequest сохранять в определенные папки - сохраняем в них
            for sub_dir in sub_dirs:
                full_path = full_path / Path(sub_dir)

        full_path.mkdir(parents=True, exist_ok=True)
        full_path = full_path / result_obj.url_request.filename
        async with aiofiles.open(full_path, "w", encoding="utf-8") as f:
            await f.write(result_obj.request_result)
            print(f"Сохранено: {full_path}")
        return result_obj

    def process_it(
        self,
        result_obj: URLResult,
    ) -> URLResult:
        raise NotImplementedError


class SaveAnyOnDisk:
    # Сохранит строковые данные на диск
    def __init__(
        self,
        folder: str = SAVERS_DEFAULTS["SAVE_FOLDER"] + "_custom_data",
    ):
        self.folder = Path(folder)

    async def a_process_it(
        self,
        data: Any,
        filename: str,
    ) -> int:
        data = str(data)
        full_path = self.folder

        full_path.mkdir(parents=True, exist_ok=True)
        full_path = full_path / filename
        async with aiofiles.open(full_path, "w", encoding="utf-8") as f:
            await f.write(data)
            print(f"Сохранено: {full_path}")
        return len(data)

    def process_it(
        self,
        result_obj: URLResult,
    ) -> URLResult:
        raise NotImplementedError
