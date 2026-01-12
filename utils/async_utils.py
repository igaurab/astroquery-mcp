"""Async utilities for astroquery MCP server."""

import asyncio
from concurrent.futures import ThreadPoolExecutor
from typing import Any, Callable, TypeVar
import functools

T = TypeVar("T")

# Thread pool for running blocking astroquery calls
_executor: ThreadPoolExecutor | None = None


def get_executor() -> ThreadPoolExecutor:
    """Get or create the thread pool executor."""
    global _executor
    if _executor is None:
        _executor = ThreadPoolExecutor(max_workers=4, thread_name_prefix="astroquery_")
    return _executor


async def run_sync(func: Callable[..., T], *args: Any, **kwargs: Any) -> T:
    """Run a synchronous function in a thread pool.

    Args:
        func: Synchronous function to run.
        *args: Positional arguments.
        **kwargs: Keyword arguments.

    Returns:
        Result of the function.
    """
    loop = asyncio.get_event_loop()
    executor = get_executor()

    # Create a partial function with kwargs
    if kwargs:
        func = functools.partial(func, **kwargs)

    return await loop.run_in_executor(executor, func, *args)


def async_wrap(func: Callable[..., T]) -> Callable[..., Any]:
    """Decorator to wrap a synchronous function as async.

    The wrapped function will run in a thread pool.

    Args:
        func: Synchronous function to wrap.

    Returns:
        Async version of the function.
    """

    @functools.wraps(func)
    async def wrapper(*args: Any, **kwargs: Any) -> T:
        return await run_sync(func, *args, **kwargs)

    return wrapper


class AsyncJobPoller:
    """Poller for async TAP jobs."""

    def __init__(
        self,
        check_interval: float = 2.0,
        max_wait: float = 300.0,
    ):
        """Initialize the poller.

        Args:
            check_interval: Seconds between status checks.
            max_wait: Maximum wait time in seconds.
        """
        self.check_interval = check_interval
        self.max_wait = max_wait

    async def wait_for_job(
        self,
        job: Any,
        status_getter: Callable[[Any], str] | None = None,
    ) -> Any:
        """Wait for an async job to complete.

        Args:
            job: Job object (e.g., from PyVO).
            status_getter: Optional function to get job status.
                          Default uses job.phase attribute.

        Returns:
            The completed job object.

        Raises:
            TimeoutError: If job doesn't complete within max_wait.
            RuntimeError: If job fails.
        """
        elapsed = 0.0

        while elapsed < self.max_wait:
            # Get current status
            if status_getter:
                status = await run_sync(status_getter, job)
            else:
                status = getattr(job, "phase", "UNKNOWN")

            # Check terminal states
            if status in ("COMPLETED", "ARCHIVED"):
                return job
            elif status in ("ERROR", "ABORTED"):
                raise RuntimeError(f"Job failed with status: {status}")

            # Wait and retry
            await asyncio.sleep(self.check_interval)
            elapsed += self.check_interval

        raise TimeoutError(f"Job did not complete within {self.max_wait}s")


async def gather_with_concurrency(
    limit: int,
    *coros: Any,
) -> list[Any]:
    """Run coroutines with limited concurrency.

    Args:
        limit: Maximum concurrent coroutines.
        *coros: Coroutines to run.

    Returns:
        List of results in order.
    """
    semaphore = asyncio.Semaphore(limit)

    async def limited_coro(coro: Any) -> Any:
        async with semaphore:
            return await coro

    return await asyncio.gather(*[limited_coro(c) for c in coros])


def shutdown_executor() -> None:
    """Shutdown the thread pool executor."""
    global _executor
    if _executor:
        _executor.shutdown(wait=False)
        _executor = None
