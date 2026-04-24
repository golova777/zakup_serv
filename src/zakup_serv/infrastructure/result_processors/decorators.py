import random
import asyncio
import functools
import inspect
import time



# Задаёт выполнение функции с задержкой, которая задаётся по
# нормальному распределению. Задержка всегда положительная,
# так как берётся по модулю.
# mu - среднее значение, sigma - стандартное отклонение
# delay взят по модулю
def add_jitter_delay(nu: float, sigma: float):
    def decorator(my_func):
        @functools.wraps(my_func)
        async def wrapper(*args, **kwargs):
            delay = abs(random.gauss(nu, sigma))
            await asyncio.sleep(delay)
            res = await my_func(*args, **kwargs)
            return res

        return wrapper

    return decorator


# статистика вызова функции - только для асинхронных функций
def a_net_stat_info():
    def decorator(my_func):
        @functools.wraps(my_func)
        async def wrapper(*args, **kwargs):
            if not hasattr(a_net_stat_info, "calls_history"):
                a_net_stat_info.calls_history = {
                    wrapper.__name__: {
                        "total_calls": 0,
                        "exec_time_avg": 0.0,
                        "exec_time_longest": 0.0,
                        "exec_time_shortest": 0.0,
                        "exec_time_total": 0.0,
                    }
                }

            if not a_net_stat_info.calls_history.get(wrapper.__name__):
                a_net_stat_info.calls_history[wrapper.__name__] = {
                    "total_calls": 0,
                    "exec_time_avg": 0.0,
                    "exec_time_longest": 0.0,
                    "exec_time_shortest": 0.0,
                    "exec_time_total": 0.0,
                }

            start_time = time.perf_counter()
            try:
                return await my_func(*args, **kwargs)

            finally:
                elapsed = time.perf_counter() - start_time
                info = a_net_stat_info.calls_history[wrapper.__name__]

                info["total_calls"] += 1
                info["exec_time_total"] += round(elapsed, 3)
                info["exec_time_avg"] = (
                        info["exec_time_total"]
                        / info["total_calls"]
                )

                if elapsed > info["exec_time_longest"]:
                    info["exec_time_longest"] = elapsed
                if info["exec_time_shortest"] == 0:
                    info["exec_time_shortest"] = elapsed
                if elapsed < info["exec_time_shortest"]:
                    info["exec_time_shortest"] = elapsed

        return wrapper

    return decorator


# статистика вызова функции - универсальный (синхронный и асинхронный)
def net_stat_info():
    """
    Универсальный декоратор статистики:
    - работает для async и sync функций
    - хранит статистику в net_stat_info.calls_history
    """

    def decorator(my_func):
        func_name = my_func.__name__

        def _ensure_slot():
            if not hasattr(net_stat_info, "calls_history"):
                net_stat_info.calls_history = {}
            if func_name not in net_stat_info.calls_history:
                net_stat_info.calls_history[func_name] = {
                    "total_calls": 0,
                    "exec_time_avg": 0.0,
                    "exec_time_longest": 0.0,
                    "exec_time_shortest": 0.0,
                    "exec_time_total": 0.0,
                }

        def _update_stats(elapsed: float):
            info = net_stat_info.calls_history[func_name]
            info["total_calls"] += 1
            info["exec_time_total"] += elapsed
            info["exec_time_avg"] = info["exec_time_total"] / info["total_calls"]

            if elapsed > info["exec_time_longest"]:
                info["exec_time_longest"] = elapsed

            if info["exec_time_shortest"] == 0.0 or elapsed < info["exec_time_shortest"]:
                info["exec_time_shortest"] = elapsed

        if inspect.iscoroutinefunction(my_func):
            @functools.wraps(my_func)
            async def async_wrapper(*args, **kwargs):
                _ensure_slot()
                start = time.perf_counter()
                try:
                    return await my_func(*args, **kwargs)
                finally:
                    _update_stats(time.perf_counter() - start)

            return async_wrapper

        @functools.wraps(my_func)
        def sync_wrapper(*args, **kwargs):
            _ensure_slot()
            start = time.perf_counter()
            try:
                return my_func(*args, **kwargs)
            finally:
                _update_stats(time.perf_counter() - start)

        return sync_wrapper

    return decorator