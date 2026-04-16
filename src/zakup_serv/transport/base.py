from dataclasses import dataclass, field
from collections.abc import Callable
from abc import ABC, abstractmethod
import inspect

from zakup_serv.domain.actual_contracts.urls import URLRequest, URLResult
from zakup_serv.infrastructure.common_helpers import normalize_signature
from zakup_serv.infrastructure.result_processors.base import DataProcessorInterface
from zakup_serv.settings import DEFAULTS

# TODO может сюда логику ретраев зашить?


@dataclass
class WebLoaderConfig:
    urls: list[URLRequest] = field(default_factory=list)
    http_method: str = DEFAULTS["HTTP_METHOD"]
    concurrent_connections: int = DEFAULTS["CONCURRENT_CONNECTIONS"]
    headers: dict = field(default_factory=lambda: DEFAULTS["HEADERS"])
    fetch_page_timeout: int = DEFAULTS["FETCH_PAGE_TIMEOUT"]
    check_ssl: bool = DEFAULTS["CHECK_SSL"]
    proxy: str | None = None

    # список обработчиков результата запроса страницы.
    # выполняются последовательно
    callbacks_list_on_result: list[Callable] = field(default_factory=list)

    def __post_init__(self):
        if not self.urls:
            raise ValueError("Список URL для загрузки не может быть пустым.")

        self.validate_callbacks_signatures()

    def validate_callbacks_signatures(self):
        ref_a_sig = normalize_signature(
            inspect.signature(DataProcessorInterface.a_process_it)
        )
        ref_sig = normalize_signature(
            inspect.signature(DataProcessorInterface.process_it)
        )

        for callback in self.callbacks_list_on_result:
            callback_sig = normalize_signature(inspect.signature(callback))
            if not (callback_sig == ref_sig or callback_sig == ref_a_sig):
                print(
                    f"Некорректный обработчик результатов скачивания. "
                    f"{callback.__name__}"
                    f"\tпередана сигнатура {callback_sig}\n"
                    f"\tожидается сигнатура {ref_sig} или {ref_a_sig}\n"
                )
                raise TypeError("Некорректный обработчик результатов скачивания")


class BaseWebLoader(ABC):
    def __init__(self, config: WebLoaderConfig):
        self.config = config
        self._load_config(config)
        # список результатов запросов URLResult
        self.url_results_list: list[URLResult] = field(default_factory=list)
        # список обработанных результатов запросов URLResult
        self.url_processed_results_list: list[URLResult] = field(default_factory=list)

    @abstractmethod
    def _load_config(self, config: WebLoaderConfig) -> None:
        raise NotImplementedError

    @abstractmethod
    async def async_fetch_pages(self) -> list[URLResult]:
        raise NotImplementedError

    # @abstractmethod
    # def fetch_pages(self) -> None:
    #    raise NotImplementedError
