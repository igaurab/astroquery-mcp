"""MCP server for astroquery - dynamically exposes all astroquery functions."""

import logging
from typing import Any

from fastmcp import FastMCP

from astroquery_mcp.auth import configure_astroquery_auth
from astroquery_mcp.executor import (
    execute_function,
    list_modules,
    list_functions,
    get_function_info,
)
from astroquery_mcp.models.errors import MCPError

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

# Create FastMCP server
mcp = FastMCP(
    "astroquery-mcp",
    instructions="""MCP server for astronomical data queries via astroquery.

Use `list_modules` to see available services (SIMBAD, ADS, MAST, etc.)
Use `list_functions` to see what functions a module provides
Use `get_function_info` to get detailed parameter info for a function
Use `execute` to call any astroquery function

Example workflow:
1. list_modules() -> see available modules
2. list_functions("simbad") -> see SIMBAD functions
3. get_function_info("simbad", "query_object") -> see parameters
4. execute("simbad", "query_object", {"object_name": "M31"}) -> run query
""",
)


def handle_error(e: Exception) -> dict[str, Any]:
    """Convert exception to error response."""
    if isinstance(e, MCPError):
        return e.to_dict()
    return {
        "error": True,
        "code": "INTERNAL_ERROR",
        "message": str(e),
        "service": "unknown",
        "recoverable": False,
        "suggestion": "Check server logs for details",
    }


@mcp.tool()
def astroquery_list_modules() -> dict[str, Any]:
    """List all available astroquery modules/services.

    Returns a list of modules like simbad, mast, ads, vizier, etc.
    with availability status.

    Returns:
        Dict with module_count and list of modules with name, class_path, available.
    """
    try:
        return list_modules()
    except Exception as e:
        return handle_error(e)


@mcp.tool()
def astroquery_list_functions(module_name: str | None = None) -> dict[str, Any]:
    """List available functions for a module.

    Args:
        module_name: Module to list functions for (e.g., 'simbad').
                    If None, lists all functions from all modules.

    Returns:
        Dict with function_count and list of functions with name, description, parameters.
    """
    try:
        return list_functions(module_name)
    except Exception as e:
        return handle_error(e)


@mcp.tool()
def astroquery_get_function_info(module_name: str, function_name: str) -> dict[str, Any]:
    """Get detailed information about a specific function.

    Args:
        module_name: Module name (e.g., 'simbad')
        function_name: Function name (e.g., 'query_object')

    Returns:
        Detailed function info including all parameters with types and descriptions.
    """
    try:
        return get_function_info(module_name, function_name)
    except Exception as e:
        return handle_error(e)


@mcp.tool()
def astroquery_execute(
    module_name: str,
    function_name: str,
    params: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Execute any astroquery function.

    Args:
        module_name: Module name (e.g., 'simbad', 'mast', 'ads', 'vizier')
        function_name: Function name (e.g., 'query_object', 'query_region')
        params: Parameters to pass to the function. Special handling:
            - Coordinates: Pass as {"ra": 10.68, "dec": 41.27} or object name string
            - Radius: Pass as {"value": 5, "unit": "arcmin"} or just a number (arcmin)

    Returns:
        Dict with success status and serialized result (tables converted to dicts).

    Examples:
        # SIMBAD object query
        execute("simbad", "query_object", {"object_name": "M31"})

        # SIMBAD region query
        execute("simbad", "query_region", {
            "coordinates": {"ra": 10.68, "dec": 41.27},
            "radius": {"value": 5, "unit": "arcmin"}
        })

        # MAST observations query
        execute("mast", "query_region", {
            "coordinates": "M31",
            "radius": 0.1
        })

        # Vizier catalog query
        execute("vizier", "query_object", {
            "object_name": "M31",
            "catalog": "II/246"
        })
    """
    try:
        return execute_function(module_name, function_name, params)
    except Exception as e:
        return handle_error(e)


def main():
    """Main entry point for the MCP server."""
    # Configure astroquery auth on startup
    auth_status = configure_astroquery_auth()
    logger.info(f"Auth configured: {auth_status}")

    # Log discovered modules
    modules = list_modules()
    available = [m["name"] for m in modules["modules"] if m["available"]]
    logger.info(f"Available modules: {available}")

    # Run the server (uses stdio by default for fastmcp deploy compatibility)
    mcp.run()



if __name__ == "__main__":
    main()
