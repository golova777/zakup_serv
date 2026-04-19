import asyncio
import functools
import random
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


# статистика вызова функции
def net_stat_info():
    def decorator(my_func):
        @functools.wraps(my_func)
        async def wrapper(*args, **kwargs):
            if not hasattr(wrapper, "calls_history"):
                wrapper.calls_history = {
                    "total_calls": 0,
                    "avg_exec_time": 0.0,
                    "total_time": 0.0,
                    "longest_exec_time": 0,
                    "shortest_exec_time": 0,
                }

            start_time = time.time()
            try:
                res = await my_func(*args, **kwargs)
                return res
            finally:
                elapsed = time.time() - start_time
                wrapper.calls_history["total_calls"] += 1
                wrapper.calls_history["total_time"] += round(elapsed, 3)
                wrapper.calls_history["avg_exec_time"] = (
                        wrapper.calls_history["total_time"]
                        / wrapper.calls_history["total_calls"]
                )

                if elapsed > wrapper.calls_history["longest_exec_time"]:
                    wrapper.calls_history["longest_exec_time"] = elapsed
                if wrapper.calls_history["shortest_exec_time"] == 0:
                    wrapper.calls_history["shortest_exec_time"] = elapsed
                if elapsed < wrapper.calls_history["shortest_exec_time"]:
                    wrapper.calls_history["shortest_exec_time"] = elapsed

        return wrapper

    return decorator
