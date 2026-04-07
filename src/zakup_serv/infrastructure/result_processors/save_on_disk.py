from pathlib import Path
from typing import Any

import aiofiles

from zakup_serv.settings import SAVERS_DEFAULTS


class SaveOnDisk:
    # Сохранит строковые данные на диск
    def __init__(
            self,
            folder: str = SAVERS_DEFAULTS["SAVE_FOLDER"],
    ):
        self.folder = Path(folder)
        self.folder.mkdir(parents=True, exist_ok=True)


    async def async_save(self, filename: str, data: Any) -> Any:
        path = self.folder / filename
        async with aiofiles.open(path, 'w', encoding='utf-8') as f:
            await f.write(data)
            print(f"Сохранено: {path}")
