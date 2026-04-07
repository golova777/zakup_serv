from zakup_serv.infrastructure.adapters import QueryParamAdapter
from zakup_serv.settings import EISContractsQueryParams


class Region:
    def __init__(self, name: str, region_id: str):
        self.name = name
        self.region_id = region_id
        self.query_param_name = EISContractsQueryParams.CUSTOMER_REGION.value
        self.query_param = QueryParamAdapter(self.query_param_name, self.region_id)

    def __repr__(self):
        return f"{self.__class__.__name__}({self.name}, {self.region_id}, {self.query_param})"


class ContractRegions:
    def __init__(self, regions: dict[str, str]):
        self.regions = self.set_regions(regions)

    def __repr__(self):
        if self.regions:
            return "\n".join([
                repr(region) for region in self.regions
            ])
        else:
            return []

    def set_regions(self, regions: dict[str, str]):
        _regions_objs = list()

        try:
            for region_name, region_id in regions.items():
                region = Region(region_name, region_id)
                _regions_objs.append(region)
        except TypeError:
            raise TypeError("Regions should be a dict with region "
                            "name as key and region id as value")

        return _regions_objs