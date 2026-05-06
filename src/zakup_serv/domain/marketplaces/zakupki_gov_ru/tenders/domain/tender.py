from dataclasses import dataclass

@dataclass
class Tender:
    number: str
    link: str
    region_name: str
    region_id: str
    publish_date: str

