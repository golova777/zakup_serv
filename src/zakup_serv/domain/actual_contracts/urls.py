from typing import Generator
from urllib.parse import urlparse, parse_qsl, urlencode, urlunparse
from zakup_serv.infrastructure.adapters import QueryParamAdapter

# генератор имён файлов
def generate_txt_filename(
        prefix: str | None = None,
        suffix: str | None = None
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





class URL:
    def __init__(self, url):
        self.result_url = url

        self.scheme: str | None = None
        self.domain: str | None = None
        self.path: str | None = None
        self.query_params: dict  | None = None
        self.filename: str = next(FILENAME_GENERATOR)


    def copy_url(self):
        return URL(self.result_url)


    def __repr__(self):
        return self.result_url


    def set_params(self, *args: QueryParamAdapter):
        # Заполним целевой URL новыми параметрами, которые передали в виде аргументов
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


