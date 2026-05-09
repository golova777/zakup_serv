import asyncio
import logging
from typing import Callable, Awaitable, Any

logger = logging.getLogger(__name__)


async def a_concurrent_runner(
        concurrency: int,
        coro_func: Callable[..., Awaitable[Any]],
        /,
        *coro_args,
        exclude_failed_results: bool = False,
) -> list[Any]:
    '''
    Запускает корутину coro_func с переданными аргументами coro_args
    в количестве concurrency параллельных задач.
    :param concurrency: Макс. количество параллельных задач, которые будут выполняться одновременно.
    :param coro_func:   Строго awaitable, которая возвращает корутину
    :param coro_args:   ТОЛЬКО tuple или dict, в зависимости от того,
                        как целевая корутина принимает аргументы
    :param exclude_failed_results:  завершившиеся исключением таски не возвращаются,
                                    как и использованный набор аргументов

    :return:    list[tuple[params, result]] - список кортежей
                (параметры таски, результат) для каждой выполненной таски.

    Ограничение
    '''

    # Обязательно должны быть параметры для тасок
    if not coro_args:
        raise ValueError(
            f"ERROR in concurrent runner: \n"
            f"input *coro_args parameters MUST must present."
            f"No instances of {coro_func.__name__} could be executed"
        )

    semaphore = asyncio.Semaphore(concurrency)

    async def semaphore_func(*args, **kwargs):
        async with semaphore:
            return await coro_func(*args, **kwargs)

    try:
        # переданы позиционные аргументы для целевой функции
        if all(isinstance(params, tuple) for params in coro_args):
            tasks = [
                asyncio.create_task(
                    semaphore_func(
                        *params
                    )
                )
                for params
                in coro_args
            ]
        elif all(isinstance(params, dict) for params in coro_args):
            tasks = [
                asyncio.create_task(
                    semaphore_func(
                        # *(unpack_coro_args_alg(params) if unpack_coro_args_alg else params)
                        **params
                    )
                )
                for params
                in coro_args
            ]
        else:
            raise TypeError(f"ERROR in concurrent runner: \n"
                            f"input coro_args parameters MUST be a tuple or dict."
                            f"No instances of {coro_func.__name__} could be executed."
                            f"got {str([type(args) for args in coro_args])}")

        tasks_results = await asyncio.gather(*tasks, return_exceptions=True)

        results = []
        error_count = 0
        for params, result in zip(coro_args, tasks_results):
            if isinstance(result, Exception):
                error_count += 1
                logger.error(
                    f"ERROR in concurrent runner: \n"
                    f"task returned exception: {type(result)}"
                    f"input coroutine {coro_func.__name__} "
                    f"with parallel tasks {concurrency} and params {params} "
                )
                if exclude_failed_results:
                    # пропустим фиксацию результатов при ошибке в таске
                    # по-умолчанию отключено
                    continue

            results.append((params, result))

        # логируем статистику выполнения
        # TODO переключить логгер результата в debug режим по окончании разработки
        # logger.debug(
        logger.info(
            f"RESULT of CONCURRENT RUNNER:\n"
            f"Done {len(tasks_results)} tasks ({concurrency} in parallel) of coroutine {coro_func.__name__}.\n"
            f"Success {len(tasks_results) - error_count}. Errors {error_count}."
        )

    except Exception as e:
        logger.exception(e, exc_info=True)
        raise e
    else:
        # вернёт список кортежей [(параметры таски, результат), ...]
        return results


