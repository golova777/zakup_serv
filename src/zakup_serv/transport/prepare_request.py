from zakup_serv.domain.actual_contracts.date_interval import DateInterval
from zakup_serv.domain.actual_contracts.price_interval import PriceInterval
from zakup_serv.domain.actual_contracts.regions import ContractRegions


class RequestConstructor:
    def __init__(
            self,
            regions: ContractRegions,
            date_interval: DateInterval,
            price_interval: PriceInterval
    ):
        pass