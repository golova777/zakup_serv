import asyncio
import logging
from pprint import pprint

from zakup_serv.domain.marketplaces.zakupki_gov_ru.contracts.domain.contracts import (
    FZ44_ContractsLists,
)
from zakup_serv.domain.marketplaces.zakupki_gov_ru.tenders.domain.new_tenders import FzNewTenders
from zakup_serv.infrastructure.logging_config import setup_logging
from zakup_serv.infrastructure.result_processors.decorators import (
    net_stat_info,
)


async def async_main():
    # Запуск логирования
    setup_logging()
    logger = logging.getLogger(__name__)

    logger.info("Service starting")

    ##########################
    callbacks = [
        # SaveOnDisk().a_process_it,
        # ContractNumsExtractor().process_it,
    ]

    regions = {
        # "77000000000": "Moskva",
        # "50000000000":"Moskva obl",
        "44000000000": "Костромская область",
        # "76000000000": "Yaroslavl region",
        # "33000000000": "Vladimir region",
        # "37000000000": "Ivanovo region",
    }

    tenders = FzNewTenders(
        regions=regions,
        from_date="05.05.2026",
        # callbacks_on_result=callbacks,
    )

    # await contracts.a_get_price_spans()
    await tenders.a_get_tenders_pages(per_page_items=50)
    # await contracts.a_get_contracts_data(concurrent=5)

    pprint(net_stat_info.calls_history)


    # ##########################
    # callbacks = [
    #     # SaveOnDisk().a_process_it,
    #     # ContractNumsExtractor().process_it,
    # ]
    #
    # regions = {
    #     # "77000000000": "Moskva",
    #     # "50000000000":"Moskva obl",
    #     "44000000000": "Костромская область",
    #     # "76000000000": "Yaroslavl region",
    #     # "33000000000": "Vladimir region",
    #     # "37000000000": "Ivanovo region",
    # }
    #
    # contracts = FZ44_ContractsLists(
    #     regions=regions,
    #     from_date="01.01.2024",
    #     to_date="31.12.2024",
    #     callbacks_on_result=callbacks,
    # )
    #
    # await contracts.a_get_price_spans()
    # await contracts.a_get_contracts_pages(per_page_items=50)
    # await contracts.a_get_contracts_data(concurrent=5)



    # статистика вызовов функций



    # pprint(net_stat_info.calls_history)


if __name__ == "__main__":
    asyncio.run(async_main())
