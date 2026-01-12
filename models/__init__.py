"""Pydantic models for astroquery MCP server."""

from astroquery_mcp.models.errors import MCPError, ErrorCode
from astroquery_mcp.models.results import (
    ServiceInfo,
    ToolSignature,
    CoordinateResult,
    PaperResult,
    ArchiveRecord,
)

__all__ = [
    "MCPError",
    "ErrorCode",
    "ServiceInfo",
    "ToolSignature",
    "CoordinateResult",
    "PaperResult",
    "ArchiveRecord",
]
