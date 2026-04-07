import asyncio


async def get_response_length(data: str | bytes | bytearray) -> int:
    # для тестовых целей - проверка процессинга результатов запросов

    await asyncio.sleep(0)
    print(f"размер загруженных данных = {len(data)}")

    return len(data)