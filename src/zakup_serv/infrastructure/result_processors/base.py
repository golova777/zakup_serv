from abc import ABC, abstractmethod

from zakup_serv.domain.actual_contracts.urls import URLRequest, URLResult


class DataProcessorInterface(ABC):
    """..."""

    @abstractmethod
    async def a_process_it(
        self,
        result_obj: URLResult,
    ) -> URLResult:
        raise NotImplementedError

    @abstractmethod
    def process_it(
        self,
        result_obj: URLResult,
    ) -> URLResult:
        raise NotImplementedError
