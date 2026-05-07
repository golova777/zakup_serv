from dataclasses import dataclass


@dataclass
class AttachedFile:
    name: str | None # фактическое имя файла при загрузке
    uid: str | None
    extension: str | None # расширение
    full_name: str | None # name.extension
    title: str | None # официальное название в блоке вложений в закупке
    link: str | None
    content: str | bytes | None




