from abc import ABC, abstractmethod

from zakup_serv.domain.marketplaces.zakupki_gov_ru.tenders.domain.tender import Tender


class BaseTenderRepository(ABC):

    # сюда можно положить конфиг, если он нужен репозиторию для работы
    marketplace_config: dict

    def __init__(self, marketplace_config: dict, **kwargs):
        self.marketplace_config = marketplace_config
        # добавим все именованные аргументы к объекту репозитория
        for key, val in kwargs.items():
            if key != "marketplace_config":
                setattr(self, key, val)


    @abstractmethod
    async def add_new_tenders(
            self,
            tenders: Tender | list[Tender]
    ) -> int:
        # добавляет только новые тендеры,
        # возвратит число добавленных новых
        raise NotImplementedError()

    @abstractmethod
    async def is_new_tender_num(self, tender: Tender, **kwargs) -> bool:
        # проверка: true если tender_number нет в репозитории, иначе false
        raise NotImplementedError()