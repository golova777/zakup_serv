import logging
from logging.config import dictConfig

"""
Если хотите JSON только в консоль (без файла), замените "handlers": 
["console", "json_file"] на "handlers": ["console"] 
и измените formatter для console на "json".
"""


def setup_logging(log_level: str = "INFO") -> None:
    dictConfig(
        {
            "version": 1,
            "disable_existing_loggers": False,
            "formatters": {
                "plain": {
                    # "format": "%(asctime)s %(levelname)s [%(filename)s:%(lineno)d] %(name)s %(message)s",
                    "format": "%(asctime)s %(levelname)s [%(filename)s:%(lineno)d] %(message)s",
                },
                "json": {  # Новый formatter для JSON
                    "class": "pythonjsonlogger.jsonlogger.JsonFormatter",
                    "format": "%(asctime)s %(name)s %(levelname)s %(filename)s %(lineno)d %(message)s",
                },
            },
            "handlers": {
                "console": {
                    "class": "logging.StreamHandler",
                    "formatter": "plain",
                    "level": log_level,
                },
                "json_file": {  # Новый handler для JSON в файл
                    "class": "logging.FileHandler",
                    "filename": "logs.json",  # Файл для JSON-логов
                    "formatter": "json",
                    "level": log_level,
                    "encoding": "utf-8",
                },
            },
            "loggers": {
                "zakup_serv": {  # корневой логгер приложения
                    "handlers": [
                        "console",
                        "json_file",
                    ],
                    # "handlers": ["console",],
                    "level": log_level,
                    "propagate": False,
                },
            },
            "root": {  # на всякий случай, для сторонних либ
                "handlers": ["console"],
                "level": "WARNING",
            },
        }
    )
