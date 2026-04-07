from dataclasses import dataclass, field
from typing import Callable

from zakup_serv.domain.actual_contracts.urls import URL
from zakup_serv.settings import DEFAULTS



class MakeUrlsList:
    pass


@dataclass
class WebLoaderConfig:
    urls: list[URL]
    http_method: str = DEFAULTS["HTTP_METHOD"]
    concurrent_connections: int = DEFAULTS["CONCURRENT_CONNECTIONS"]
    # headers: dict = DEFAULTS["HEADERS"]
    headers: dict = field(default_factory=lambda: DEFAULTS["HEADERS"].copy())
    fetch_page_timeout: int = DEFAULTS["FETCH_PAGE_TIMEOUT"]
    check_ssl: bool = DEFAULTS["CHECK_SSL"]
    callback_on_result: Callable = None





class WebLoader:
    def __init__(self, config: WebLoaderConfig):
        self.config = WebLoaderConfig




