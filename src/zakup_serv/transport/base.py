from dataclasses import dataclass
from abc import ABC, abstractmethod

from zakup_serv.settings import DEFAULTS



class MakeUrlsList:
    pass


@dataclass(slots=True)
class WebLoaderConfig:
    urls: list[str]
    http_method: str = DEFAULTS["HTTP_METHOD"]
    concurrent_connections: int = DEFAULTS["CONCURRENT_CONNECTIONS"]
    headers: dict = DEFAULTS["HEADERS"]
    fetch_page_timeout: int = DEFAULTS["FETCH_PAGE_TIMEOUT"]
    check_ssl: bool = DEFAULTS["CHECK_SSL"]
    callback_on_result: Callable = None





class WebLoader:
    def __init__(self, config: WebLoaderConfig):
        self.config = WebLoaderConfig




