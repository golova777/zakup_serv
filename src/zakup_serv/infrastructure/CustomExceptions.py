import logging


# Подключим логирование
logger = logging.getLogger(__name__)

class RetriableNetworkException(Exception):
    """Ошибка сети, которая может быть повторена.
    Например, при загрузке страницы возникла ошибка сети,
    но при повторной попытке она может быть успешно загружена.
    """

    pass


class NotRetriableNetworkException(Exception):
    """Ошибка сети, которая не может быть повторена."""

    pass


class ExceededRetryAttemptsException(Exception):
    """Исчерпаны попытки скачать страницы"""

    pass


class NoNewContractsException(Exception):
    """Нет новых контрактов при загрузке.
    Либо вообще нет записей,
    либо те что загружены - все уже ака-то обработаны
    """

    pass


class NoDataLoadedException(Exception):
    """Данные не были загружены, хотя загрузка прошла без ошибок.
    Например, при загрузке страницы не было найдено данных, которые должны были быть там.
    """
    pass


class FailedContractFetchException(Exception):
    """Ошибка при загрузке контракта.
    Например, при загрузке страницы контракта возникла ошибка сети, или страница была
    """
    def __init__(self, contract_num: str, ecp_type, message: str):
        self.contract_num = contract_num
        self.ecp_type = ecp_type
        self.message = message
        super().__init__(
            f"Failed fetching contract num {self.contract_num} "
            f"with exception {self.ecp_type} "
            f"{self.message}"
        )


class InconsistentDataException(Exception):
    def __init__(self, message: str, **kwargs):
        self.message = message

        super().__init__(
            f"Inconsistent data.\n"
            f"message: {self.message}\n"
            f"kwargs: {kwargs}"
        )

        logger.error(
            f"Inconsistent data.\n"
            f"message: {self.message}\n"
            f"kwargs: {kwargs}"
        )
