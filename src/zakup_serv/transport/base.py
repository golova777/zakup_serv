from dataclasses import dataclass, field
from collections.abc import Callable
from abc import ABC, abstractmethod
from typing import Any

from zakup_serv.domain.actual_contracts.urls import URLRequest, URLResult
from zakup_serv.settings import DEFAULTS




class MakeUrlsList:
    pass


@dataclass
class WebLoaderConfig:
    urls: list[URLRequest]
    http_method: str = DEFAULTS["HTTP_METHOD"]
    concurrent_connections: int = DEFAULTS["CONCURRENT_CONNECTIONS"]
    # headers: dict = DEFAULTS["HEADERS"]
    headers: dict = field(default_factory=lambda: DEFAULTS["HEADERS"].copy())
    fetch_page_timeout: int = DEFAULTS["FETCH_PAGE_TIMEOUT"]
    check_ssl: bool = DEFAULTS["CHECK_SSL"]

    # Обработчик применяется сразу после скачивания данных по сети
    callback_on_instant_result: Callable[[Any, URLRequest], Any] = None
    # Обработчик применяется после завершения всех запросов
    callback_on_final_result: Callable[[Any, URLRequest], Any] = None


class BaseWebLoaderConfig(ABC):
    def __init__(self, config: WebLoaderConfig):
        self.config = config
        self._load_config(config)

    @abstractmethod
    def _load_config(self, config: WebLoaderConfig) -> None:
        raise NotImplementedError

    @abstractmethod
    async def async_fetch_pages(self) -> list[URLResult]:
        raise NotImplementedError

    #@abstractmethod
    #def fetch_pages(self) -> None:
    #    raise NotImplementedError


