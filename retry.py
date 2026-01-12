"""Retry and backoff utilities for astroquery MCP server."""

import asyncio
import functools
import logging
from typing import Any, Callable, TypeVar

from tenacity import (
    retry,
    stop_after_attempt,
    wait_exponential,
    retry_if_exception_type,
    before_sleep_log,
    RetryError,
)

from astroquery_mcp.config import get_config
from astroquery_mcp.models.errors import MCPError, ErrorCode

logger = logging.getLogger(__name__)

T = TypeVar("T")

# Common retryable exceptions
RETRYABLE_EXCEPTIONS = (
    TimeoutError,
    ConnectionError,
    ConnectionResetError,
    ConnectionRefusedError,
)


def with_retry(
    max_retries: int | None = None,
    backoff_factor: float | None = None,
    retryable_exceptions: tuple = RETRYABLE_EXCEPTIONS,
) -> Callable:
    """Decorator to add retry with exponential backoff to a function.

    Args:
        max_retries: Maximum number of retry attempts. Uses config default if None.
        backoff_factor: Multiplier for exponential backoff. Uses config default if None.
        retryable_exceptions: Tuple of exception types to retry on.

    Returns:
        Decorated function with retry logic.
    """
    config = get_config()

    if max_retries is None:
        max_retries = config.defaults.max_retries
    if backoff_factor is None:
        backoff_factor = config.defaults.backoff_factor

    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        @retry(
            stop=stop_after_attempt(max_retries + 1),
            wait=wait_exponential(multiplier=backoff_factor, min=1, max=60),
            retry=retry_if_exception_type(retryable_exceptions),
            before_sleep=before_sleep_log(logger, logging.WARNING),
            reraise=True,
        )
        @functools.wraps(func)
        def sync_wrapper(*args: Any, **kwargs: Any) -> T:
            return func(*args, **kwargs)

        @retry(
            stop=stop_after_attempt(max_retries + 1),
            wait=wait_exponential(multiplier=backoff_factor, min=1, max=60),
            retry=retry_if_exception_type(retryable_exceptions),
            before_sleep=before_sleep_log(logger, logging.WARNING),
            reraise=True,
        )
        @functools.wraps(func)
        async def async_wrapper(*args: Any, **kwargs: Any) -> T:
            return await func(*args, **kwargs)

        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        return sync_wrapper

    return decorator


async def run_with_timeout(
    coro: Any,
    timeout: float | None = None,
    service: str = "unknown",
) -> Any:
    """Run a coroutine with timeout.

    Args:
        coro: Coroutine to run.
        timeout: Timeout in seconds. Uses config default if None.
        service: Service name for error messages.

    Returns:
        Result of the coroutine.

    Raises:
        MCPError: If the operation times out.
    """
    config = get_config()

    if timeout is None:
        timeout = config.defaults.timeout

    try:
        return await asyncio.wait_for(coro, timeout=timeout)
    except asyncio.TimeoutError:
        raise MCPError(
            code=ErrorCode.TIMEOUT_ERROR,
            message=f"Operation timed out after {timeout}s",
            service=service,
            recoverable=True,
            suggestion="Try again or increase timeout",
            details={"timeout": timeout},
        )


def run_sync_with_retry(
    func: Callable[..., T],
    *args: Any,
    max_retries: int | None = None,
    backoff_factor: float | None = None,
    service: str = "unknown",
    **kwargs: Any,
) -> T:
    """Run a synchronous function with retry logic.

    This is useful for wrapping astroquery functions that are synchronous.

    Args:
        func: Function to call.
        *args: Positional arguments for the function.
        max_retries: Maximum retry attempts.
        backoff_factor: Backoff multiplier.
        service: Service name for error messages.
        **kwargs: Keyword arguments for the function.

    Returns:
        Result of the function.

    Raises:
        MCPError: If all retries fail.
    """
    config = get_config()

    if max_retries is None:
        max_retries = config.defaults.max_retries
    if backoff_factor is None:
        backoff_factor = config.defaults.backoff_factor

    last_error = None
    for attempt in range(max_retries + 1):
        try:
            return func(*args, **kwargs)
        except RETRYABLE_EXCEPTIONS as e:
            last_error = e
            if attempt < max_retries:
                wait_time = backoff_factor ** attempt
                logger.warning(
                    f"Attempt {attempt + 1}/{max_retries + 1} failed for {service}: {e}. "
                    f"Retrying in {wait_time}s..."
                )
                import time

                time.sleep(wait_time)
            else:
                logger.error(f"All {max_retries + 1} attempts failed for {service}")

    raise MCPError(
        code=ErrorCode.SERVICE_ERROR,
        message=f"Operation failed after {max_retries + 1} attempts: {last_error}",
        service=service,
        recoverable=True,
        suggestion="The service may be temporarily unavailable. Try again later.",
        details={"last_error": str(last_error), "attempts": max_retries + 1},
    )


class RateLimiter:
    """Simple rate limiter for service calls."""

    def __init__(self, requests_per_second: float = 10.0):
        """Initialize rate limiter.

        Args:
            requests_per_second: Maximum requests per second.
        """
        self.min_interval = 1.0 / requests_per_second
        self._last_request: float = 0.0
        self._lock = asyncio.Lock()

    async def acquire(self) -> None:
        """Wait until a request is allowed."""
        async with self._lock:
            import time

            now = time.monotonic()
            elapsed = now - self._last_request
            if elapsed < self.min_interval:
                await asyncio.sleep(self.min_interval - elapsed)
            self._last_request = time.monotonic()


# Rate limiters for different services
_rate_limiters: dict[str, RateLimiter] = {}


def get_rate_limiter(service: str) -> RateLimiter:
    """Get or create a rate limiter for a service.

    Args:
        service: Service name.

    Returns:
        RateLimiter instance for the service.
    """
    if service not in _rate_limiters:
        config = get_config()
        rate_config = config.rate_limits.get(service)
        rps = rate_config.requests_per_second if rate_config else 10.0
        _rate_limiters[service] = RateLimiter(rps)
    return _rate_limiters[service]
