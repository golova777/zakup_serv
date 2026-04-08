from typing import Generator, Any
from urllib.parse import urlparse, parse_qsl, urlencode, urlunparse
from zakup_serv.infrastructure.adapters import QueryParamAdapter

# генератор имён файлов
def generate_txt_filename(
        prefix: str | None = None,
        suffix: str | None = None,
        externsion: str | None = None,
) -> Generator:
    page_num: int = 1
    while True:
        _prefix = prefix or ""
        _suffix = suffix or ""
        filename = prefix + str(page_num) + _suffix + ".txt"
        #print(f"Сгенерировано имя файла: {filename}")
        yield filename

        page_num += 1


FILENAME_GENERATOR = generate_txt_filename("page_")


# TODO
class URLResult:
    ''' Результат выполнения запроса представителем транспортногослоя '''

    def __init__(self, request_result: Any):
        self._url_request_obj: URLRequest | None = None
        self.request_result: Any = request_result
        self.raised_exceptions: Exception | None = None

    def __len__(self):
        if isinstance(self.request_result, str) or isinstance(self.request_result, bytes):
            return len(self.request_result)
        return 0

    def _set_raised_exceptions(self, request_result: Any):
        if isinstance(request_result, Exception):
            self.raised_exceptions = request_result

    def set_url_request(self, url_request: URLRequest):
        self._url_request_obj = url_request

    def get_url_request(self) -> URLRequest | None:
        return self._url_request_obj



class URLRequest:
    ''' Объект запроса который будет передаваться представителю транспортного слоя '''

    def __init__(self, url):
        self.result_url = url

        self.scheme: str | None = None
        self.domain: str | None = None
        self.path: str | None = None
        self.query_params: dict  | None = None
        self.filename: str = next(FILENAME_GENERATOR)

        self.actual_request: Any = None

        self.callback_on_instant_result: Any = None
        self.callback_on_final_result: Any = None


    def copy_url(self):
        return URLRequest(self.result_url)


    def __repr__(self):
        return self.result_url


    def set_params(self, *args: QueryParamAdapter):
        # Заполним целевой URLRequest новыми параметрами, которые передали в виде аргументов
        # типа адаптера QueryParamAdapter

        all_args_have_correct_type = all([
            isinstance(arg, QueryParamAdapter) for arg in args
        ])
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
        else:
            raise TypeError(f"Все аргументы в {self.__class__.__name__} дб QueryParamAdapter", args)


