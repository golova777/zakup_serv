from abc import ABC, abstractmethod

from zakup_serv.infrastructure.urls import (
    URLResult,
)


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
