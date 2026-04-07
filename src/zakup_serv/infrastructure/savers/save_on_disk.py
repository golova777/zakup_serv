import aiofiles

from zakup_serv.settings import SAVERS_DEFAULTS


class SaveOnDisk:
    # Сохранит строковые данные на диск
    def __init__(
            self,
            filename: str,
            data: str,
            folder: str = SAVERS_DEFAULTS["SAVE_FOLDER"],
            file_name_extension: str = SAVERS_DEFAULTS["FILE_EXTENSION"],
    ):
        self.filename = filename
        self.folder = folder
        self.file_name_extension = file_name_extension
        self.data = data

    async def async_save(self):
        async with aiofiles.open(self.folder + self.filename, 'w', encoding='utf-8') as f:
            await f.write(self.data)
            print(f"Сохранено: {self.folder + self.filename}")
