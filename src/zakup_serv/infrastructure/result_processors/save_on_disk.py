from pathlib import Path
from typing import Any

import aiofiles

from zakup_serv.infrastructure.urls import URLResult
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
    def __init__(self):
        # self.folder: str = SAVERS_DEFAULTS["SAVE_FOLDER"]
        pass

    @staticmethod
    async def a_process_it(
        data: str | bytes | Any,
        filename: str,
        folders: list[str | Path] | Path | None = None,
    ) -> int:

        # для любых данных кроме bytes - преобразуем к строковому представлению
        if not isinstance(data, bytes):
            data = str(data)

        full_path = Path(SAVERS_DEFAULTS["SAVE_FOLDER"])

        if folders:
            # в принципе заданы директории сохранения
            if isinstance(folders, Path):
                # Передан Path аргумент - конечная директория сохранения
                full_path = folders
            elif isinstance(folders, list) and len(folders) > 0:
                # передан список (либо строк, либо объектов Path)

                # базовая директория для всех сохранений
                full_path = Path(SAVERS_DEFAULTS["SAVE_FOLDER"])
                for folder in folders:
                    # проходим каждый элемент в списке директорий
                    if isinstance(folder, Path):
                        # имеем объект Path - добавляем его к пути сохранения без преобразований
                        full_path = full_path / folder
                    elif isinstance(folder, str):
                        # имеем строку - преобразуем ее в Path и добавляем к пути сохранения
                        full_path = full_path / Path(folder)

        full_path.mkdir(parents=True, exist_ok=True)
        full_path = full_path / filename

        if isinstance(data, bytes):
            # режим полной перезаписи файла в бинарном режиме
            async with aiofiles.open(full_path, "wb") as f:
                await f.write(data)
            return len(data)
        elif isinstance(data, str):
            # режим полной перезаписи файла
            async with aiofiles.open(full_path, "w", encoding="utf-8") as f:
                await f.write(data)
            return len(data)
        else:
            return 0


    def process_it(
        self,
        result_obj: URLResult,
    ) -> URLResult:
        raise NotImplementedError
