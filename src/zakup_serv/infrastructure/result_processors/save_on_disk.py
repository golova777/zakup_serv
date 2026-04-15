from pathlib import Path
from typing import Any
import aiofiles

from zakup_serv.domain.actual_contracts.urls import URLResult
from zakup_serv.infrastructure.result_processors.base import DataProcessorInterface
from zakup_serv.settings import SAVERS_DEFAULTS


class SaveOnDisk(DataProcessorInterface):
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

        self.folder.mkdir(parents=True, exist_ok=True)
        path = self.folder / result_obj.url_request.filename
        async with aiofiles.open(path, 'w', encoding='utf-8') as f:
            await f.write(result_obj.request_result)
            print(f"Сохранено: {path}")
        return result_obj

    def process_it(self,
                   result_obj: URLResult,
                   ) -> URLResult:
        raise NotImplementedError
