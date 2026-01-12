"""HTTP client for fetching external resources (GCN, publisher URLs)."""

import logging
from typing import Any

import httpx

from config import get_config
from models.errors import MCPError, ErrorCode
from retry import with_retry

logger = logging.getLogger(__name__)

# Default headers for HTTP requests
DEFAULT_HEADERS = {
    "User-Agent": "astroquery-mcp/0.1.0 (https://github.com/astroquery-mcp)",
    "Accept": "application/json, text/html, text/plain, */*",
}


@with_retry()
async def fetch_url(
    url: str,
    headers: dict[str, str] | None = None,
    timeout: float | None = None,
    follow_redirects: bool = True,
) -> dict[str, Any]:
    """Fetch content from a URL.

    Args:
        url: URL to fetch.
        headers: Optional additional headers.
        timeout: Request timeout in seconds.
        follow_redirects: Whether to follow redirects.

    Returns:
        Dictionary with 'status', 'content_type', 'content', and 'headers'.

    Raises:
        MCPError: If the request fails.
    """
    config = get_config()
    if timeout is None:
        timeout = config.defaults.timeout

    request_headers = DEFAULT_HEADERS.copy()
    if headers:
        request_headers.update(headers)

    try:
        async with httpx.AsyncClient(
            timeout=timeout, follow_redirects=follow_redirects
        ) as client:
            response = await client.get(url, headers=request_headers)

            content_type = response.headers.get("content-type", "")

            # Determine content based on type
            if "json" in content_type:
                content = response.json()
            elif "text" in content_type or "html" in content_type:
                content = response.text
            else:
                content = response.content

            return {
                "status": response.status_code,
                "content_type": content_type,
                "content": content,
                "headers": dict(response.headers),
                "url": str(response.url),
            }

    except httpx.TimeoutException:
        raise MCPError(
            code=ErrorCode.TIMEOUT_ERROR,
            message=f"Request timed out after {timeout}s",
            service="http",
            recoverable=True,
            suggestion="Try again or increase timeout",
            details={"url": url, "timeout": timeout},
        )
    except httpx.HTTPStatusError as e:
        raise MCPError(
            code=ErrorCode.SERVICE_ERROR,
            message=f"HTTP error: {e.response.status_code}",
            service="http",
            recoverable=e.response.status_code >= 500,
            suggestion="Check the URL or try again later",
            details={"url": url, "status": e.response.status_code},
        )
    except Exception as e:
        raise MCPError(
            code=ErrorCode.SERVICE_ERROR,
            message=f"Request failed: {str(e)}",
            service="http",
            recoverable=True,
            suggestion="Check network connectivity",
            details={"url": url, "error": str(e)},
        )


async def fetch_json(url: str, **kwargs: Any) -> Any:
    """Fetch JSON from a URL.

    Args:
        url: URL to fetch.
        **kwargs: Additional arguments for fetch_url.

    Returns:
        Parsed JSON content.

    Raises:
        MCPError: If request fails or content is not JSON.
    """
    kwargs.setdefault("headers", {})
    kwargs["headers"]["Accept"] = "application/json"

    result = await fetch_url(url, **kwargs)

    if isinstance(result["content"], dict | list):
        return result["content"]

    # Try to parse if it wasn't auto-detected as JSON
    import json

    try:
        return json.loads(result["content"])
    except (json.JSONDecodeError, TypeError):
        raise MCPError(
            code=ErrorCode.SERVICE_ERROR,
            message="Response is not valid JSON",
            service="http",
            recoverable=False,
            suggestion="The endpoint may not return JSON",
            details={"url": url, "content_type": result["content_type"]},
        )


async def fetch_text(url: str, **kwargs: Any) -> str:
    """Fetch text content from a URL.

    Args:
        url: URL to fetch.
        **kwargs: Additional arguments for fetch_url.

    Returns:
        Text content.
    """
    result = await fetch_url(url, **kwargs)

    if isinstance(result["content"], str):
        return result["content"]
    elif isinstance(result["content"], bytes):
        return result["content"].decode("utf-8", errors="replace")
    else:
        return str(result["content"])


async def download_file(
    url: str,
    output_path: str | None = None,
    timeout: float = 300.0,
) -> dict[str, Any]:
    """Download a file from a URL.

    Args:
        url: URL to download.
        output_path: Path to save file. If None, returns content in memory.
        timeout: Download timeout in seconds.

    Returns:
        Dictionary with download info.
    """
    try:
        async with httpx.AsyncClient(timeout=timeout, follow_redirects=True) as client:
            response = await client.get(url, headers=DEFAULT_HEADERS)
            response.raise_for_status()

            content_length = response.headers.get("content-length")
            content_type = response.headers.get("content-type", "")

            result = {
                "status": response.status_code,
                "content_type": content_type,
                "size": int(content_length) if content_length else len(response.content),
                "url": str(response.url),
            }

            if output_path:
                with open(output_path, "wb") as f:
                    f.write(response.content)
                result["saved_to"] = output_path
            else:
                result["content"] = response.content

            return result

    except Exception as e:
        raise MCPError(
            code=ErrorCode.SERVICE_ERROR,
            message=f"Download failed: {str(e)}",
            service="http",
            recoverable=True,
            suggestion="Check the URL or try again later",
            details={"url": url, "error": str(e)},
        )
