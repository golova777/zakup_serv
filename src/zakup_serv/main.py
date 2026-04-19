import asyncio
import logging
from pprint import pprint

from zakup_serv.domain.marketplaces.zakupki_gov_ru.contracts.domain.contracts import (
    FZ44_ContractsLists,
)
from zakup_serv.infrastructure.logging_config import setup_logging
from zakup_serv.transport.aiohttp_dl import AiohttpDlTransport


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

    # regions = {
    #     "kostroma": "44000000000",
    #     "yaroslavl": "76000000000",
    #     "vladimir": "33000000000",
    #
    # }

    regions = {
        "Moskva": "77000000000",
        "Moskva obl": "50000000000",
        "Костромская область": "44000000000",
        "Yaroslavl region": "76000000000",
        "Vladimir region": "33000000000",
        "Ivanovo region": "37000000000",
    }

    contract_list_pages = FZ44_ContractsLists(
        regions=regions,
        from_date="01.01.2024",
        to_date="31.12.2024",
        callbacks_on_result=callbacks,
    )

    await contract_list_pages.a_get_all_contract_lists_pages()

    pprint(AiohttpDlTransport._a_download.calls_history)


if __name__ == "__main__":
    asyncio.run(async_main())
