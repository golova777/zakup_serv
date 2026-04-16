from typing import Generator, Any
import logging
from urllib.parse import urlparse, parse_qsl, urlencode, urlunparse

from zakup_serv.infrastructure.adapters import QueryParamAdapter

# Подключим логирование
logger = logging.getLogger(__name__)


# генератор имён файлов
def generate_txt_filename(
    prefix: str | None = None,
    suffix: str | None = None,
) -> Generator:
    page_num: int = 1
    while True:
        _prefix = prefix or ""
        _suffix = suffix or ""
        filename = _prefix + str(page_num) + _suffix + ".txt"
        # print(f"Сгенерировано имя файла: {filename}")
        yield filename

        page_num += 1


FILENAME_GENERATOR = generate_txt_filename("page_")


class URLResult:
    """Результат выполнения запроса представителем транспортного слоя"""

    def __init__(
        self,
        request_result: Any = None,
        url_request: URLRequest | None = None,
    ):

        self.request_result: Any = self.set_request_result(request_result)
        self.url_request: URLRequest | None = self.set_url_request(url_request)
        self.downloading_raised_exceptions: Exception | None = None

    def __len__(self):
        if isinstance(self.request_result, str) or isinstance(
            self.request_result, bytes
        ):
            return len(self.request_result)
        return 0

    def set_request_result(self, request_result: Any):
        if isinstance(request_result, Exception):
            self.downloading_raised_exceptions = request_result
            return None
        else:
            return request_result

    def set_url_request(self, url_request: URLRequest):
        if url_request:
            return url_request
        else:
            return None


class URLRequest:
    """Объект запроса который будет передаваться представителю транспортного слоя"""

    def __init__(self, url):
        self.result_url = url

        self.scheme: str | None = None
        self.domain: str | None = None
        self.path: str | None = None
        self.query_params: dict | None = None
        self.filename: str = next(FILENAME_GENERATOR)

        self.callback_on_instant_result: Any = None
        self.callback_on_final_result: Any = None
        # Статус и код ответа сервера
        self.ok: bool = False
        self.status_code: int | None = None
        # Секция ретраев
        self.attempt: int = 0

    def copy_url(self):
        return URLRequest(self.result_url)

    def __repr__(self):
        return self.result_url

    def set_params(self, *args: QueryParamAdapter):
        # Заполним целевой URLRequest новыми параметрами, которые передали в виде аргументов
        # типа адаптера QueryParamAdapter

        all_args_have_correct_type = all(
            [isinstance(arg, QueryParamAdapter) for arg in args]
        )
        if all_args_have_correct_type:
            url_parts = list(urlparse(self.result_url))

            query_params = dict(parse_qsl(url_parts[4]))

            # на всякий сохраним компоненты ссылки
            self.scheme = url_parts[0]
            self.domain = url_parts[1]
            self.path = url_parts[2]
            self.query_params = query_params

            for param in args:
                query_params[param.param_name] = param.param_value

            url_parts[4] = urlencode(query_params)
            self.result_url = urlunparse(url_parts)

            logger.debug(
                f"URL создан:  {self.result_url} ===== для параметров: {self.query_params}"
            )
        else:
            logger.critical(
                f"Ошибка при установке параметров URL: все аргументы должны быть "
                f"типа QueryParamAdapter, но получены аргументы "
                f"с типами: {[type(arg) for arg in args if not isinstance(arg, QueryParamAdapter)]}"
            )
            raise TypeError(
                f"Все аргументы в {self.__class__.__name__} дб QueryParamAdapter", args
            )
