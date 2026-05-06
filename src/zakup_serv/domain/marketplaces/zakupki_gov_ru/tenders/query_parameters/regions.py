from zakup_serv.infrastructure.adapters import QueryParamAdapter
from zakup_serv.domain.marketplaces.zakupki_gov_ru.tenders.query_parameters.base import QueryParam
from zakup_serv.domain.marketplaces.zakupki_gov_ru.tenders.tender_config import TENDER_MARKETPLACE_INFO

query_params = TENDER_MARKETPLACE_INFO["EIS"]["query_params"]


class Region(QueryParam):
    def __init__(self, region_name: str, region_id: str):
        super().__init__()
        self.region_name = region_name
        self.region_id = region_id
        self.query_param_name = query_params.CUSTOMER_REGION.value
        self.query_param = QueryParamAdapter(self.query_param_name, self.region_id)

    def __repr__(self):
        return (f"{self.__class__.__name__}(region_name={self.region_name}, "
                f"region_id={self.region_id}, query_param_name={self.query_param})")


class Regions:
    def __init__(self, regions: dict[str, str]):
        self.regions = self.set_regions(regions)

    def __repr__(self):
        if self.regions:
            return "\n".join([repr(region) for region in self.regions])
        else:
            return []

    def set_regions(self, regions: dict[str, str]):
        _regions_objs = list()

        try:
            for region_id, region_name in regions.items():
                region = Region(region_name, region_id)
                _regions_objs.append(region)
        except TypeError:
            raise TypeError(
                "Regions should be a dict with region "
                "name as key and region id as value"
            )

        return _regions_objs
