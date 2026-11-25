import logging
import time
from functools import wraps

logger = logging.getLogger(__name__)


def monitor_execution(func):

    @wraps(func)
    async def wrapper(*args, **kwargs):

        start_time = time.perf_counter()

        try:

            result = await func(*args, **kwargs)

            execution_time = (
                time.perf_counter() - start_time
            )

            logger.info(
                "Function=%s Status=SUCCESS Duration=%.3fs",
                func.__name__,
                execution_time
            )

            return result

        except Exception:

            execution_time = (
                time.perf_counter() - start_time
            )

            logger.exception(
                "Function=%s Status=FAILED Duration=%.3fs",
                func.__name__,
                execution_time
            )

            raise

    return wrapper
