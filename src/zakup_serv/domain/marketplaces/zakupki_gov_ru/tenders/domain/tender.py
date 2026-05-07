from dataclasses import dataclass
from typing import Any

from zakup_serv.domain.marketplaces.zakupki_gov_ru.tenders.domain.tender_types import TenderType


@dataclass
class Tender:
    number: str
    link: str
    region_name: str
    region_id: str
    publish_date: str
    tender_type: TenderType
    content: Any | None = None

