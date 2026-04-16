import asyncio
import logging

from zakup_serv.domain.marketplaces.zakupki_gov_ru.contracts.domain.contracts import (
    FZ44_ContractsLists,
)
from zakup_serv.infrastructure.logging_config import setup_logging
from zakup_serv.infrastructure.result_processors.extract_contract_nums import (
    ContractNumsExtractor,
)
from zakup_serv.infrastructure.result_processors.save_on_disk import SaveOnDisk


async def async_main():
    # Запуск логирования
    setup_logging()
    logger = logging.getLogger(__name__)

    logger.info("Service starting")

    ##########################
    callbacks = [
        SaveOnDisk().a_process_it,
        ContractNumsExtractor().process_it,
    ]

    regions = {
        "kostroma": "44000000000",
    }

    contract_list_pages = FZ44_ContractsLists(
        regions=regions,
        from_date="01.01.2026",
        to_date="01.05.2026",
        callbacks_on_result=callbacks,
    )

    await contract_list_pages.a_get_all_contract_lists_pages()


if __name__ == "__main__":
    asyncio.run(async_main())
