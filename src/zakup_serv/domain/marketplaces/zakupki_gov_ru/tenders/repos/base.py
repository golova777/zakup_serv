from abc import ABC, abstractmethod

from zakup_serv.domain.marketplaces.zakupki_gov_ru.tenders.domain.tender import Tender


class BaseTenderRepository(ABC):

    @abstractmethod
    def add_new_tenders(
            self,
            tenders: Tender | list[Tender]
    ) -> int:
        # добавляет только новые тендеры,
        # возвратит число добавленных новых
        raise NotImplementedError()


    @abstractmethod
    def is_new_tender_num(self, tender_number: str, **kwargs) -> bool:
        # проверка: true если tender_number нет в репозитории, иначе false
        raise NotImplementedError()