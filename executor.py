"""Execute astroquery functions dynamically and serialize results."""

import importlib
import logging
from typing import Any

from astropy.table import Table
from astropy.coordinates import SkyCoord
from astropy import units as u

from introspection import ASTROQUERY_MODULES, discover_all_functions
from utils.table_utils import table_to_dict
from models.errors import MCPError, ErrorCode

logger = logging.getLogger(__name__)

# Cache for loaded classes
_class_cache: dict[str, Any] = {}


def get_class_instance(module_name: str) -> Any:
    """Get or create an instance/class for a module.

    Args:
        module_name: Short module name (e.g., 'simbad')

    Returns:
        The class or instance to call methods on.
    """
    if module_name in _class_cache:
        return _class_cache[module_name]

    if module_name not in ASTROQUERY_MODULES:
        raise MCPError(
            code=ErrorCode.VALIDATION_ERROR,
            message=f"Unknown module: {module_name}",
            service="executor",
            recoverable=False,
            suggestion=f"Available modules: {', '.join(ASTROQUERY_MODULES.keys())}",
        )

    class_path = ASTROQUERY_MODULES[module_name]

    try:
        parts = class_path.rsplit(".", 1)
        if len(parts) == 2:
            module_path, class_name = parts
            module = importlib.import_module(module_path)
            cls = getattr(module, class_name)
        else:
            cls = importlib.import_module(class_path)

        _class_cache[module_name] = cls
        return cls

    except ImportError as e:
        raise MCPError(
            code=ErrorCode.SERVICE_ERROR,
            message=f"Could not import {module_name}: {e}",
            service="executor",
            recoverable=False,
            suggestion="Check that astroquery is installed with required extras",
        )


def prepare_argument(value: Any, param_name: str) -> Any:
    """Convert argument values to appropriate types for astroquery.

    Handles special cases like coordinates, units, etc.
    """
    if value is None:
        return None

    # Handle coordinate-like parameters
    coord_params = {"coordinates", "coord", "coords", "position", "pos", "target"}
    if param_name.lower() in coord_params or "coord" in param_name.lower():
        if isinstance(value, dict):
            # Convert dict with ra/dec to SkyCoord
            if "ra" in value and "dec" in value:
                return SkyCoord(
                    ra=value["ra"] * u.deg,
                    dec=value["dec"] * u.deg,
                    frame=value.get("frame", "icrs"),
                )
        elif isinstance(value, str):
            # Try to parse as object name or coordinate string
            try:
                return SkyCoord.from_name(value)
            except Exception:
                try:
                    return SkyCoord(value)
                except Exception:
                    return value

    # Handle radius parameters
    radius_params = {"radius", "rad", "search_radius", "cone_radius"}
    if param_name.lower() in radius_params or "radius" in param_name.lower():
        if isinstance(value, dict):
            # {"value": 5, "unit": "arcmin"}
            val = value.get("value", value.get("v", 1))
            unit_str = value.get("unit", value.get("u", "arcmin"))
            unit = getattr(u, unit_str, u.arcmin)
            return val * unit
        elif isinstance(value, (int, float)):
            # Assume arcmin by default
            return value * u.arcmin

    # Handle width/height for box searches
    if param_name.lower() in {"width", "height"}:
        if isinstance(value, (int, float)):
            return value * u.arcmin
        elif isinstance(value, dict):
            val = value.get("value", 1)
            unit_str = value.get("unit", "arcmin")
            unit = getattr(u, unit_str, u.arcmin)
            return val * unit

    return value


def serialize_result(result: Any) -> Any:
    """Serialize astroquery results to JSON-compatible format.

    Handles Astropy Tables, SkyCoords, Quantities, etc.
    """
    if result is None:
        return None

    # Astropy Table
    if isinstance(result, Table):
        return table_to_dict(result)

    # List of Tables
    if isinstance(result, list) and result and isinstance(result[0], Table):
        return [table_to_dict(t) for t in result]

    # SkyCoord
    if isinstance(result, SkyCoord):
        return {
            "ra_deg": result.ra.deg,
            "dec_deg": result.dec.deg,
            "frame": result.frame.name,
        }

    # Astropy Quantity
    if hasattr(result, "value") and hasattr(result, "unit"):
        return {"value": float(result.value), "unit": str(result.unit)}

    # Dict - recursively serialize
    if isinstance(result, dict):
        return {k: serialize_result(v) for k, v in result.items()}

    # List - recursively serialize
    if isinstance(result, list):
        return [serialize_result(item) for item in result]

    # Numpy types
    if hasattr(result, "item"):
        return result.item()

    # Bytes
    if isinstance(result, bytes):
        return result.decode("utf-8", errors="replace")

    return result


def execute_function(
    module_name: str,
    function_name: str,
    params: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Execute an astroquery function dynamically.

    Args:
        module_name: Short module name (e.g., 'simbad')
        function_name: Method name (e.g., 'query_object')
        params: Parameters to pass to the function

    Returns:
        Serialized result with metadata.
    """
    params = params or {}

    try:
        # Configure authentication on-demand for services that need it
        if module_name in ("ads", "mast", "mast_catalogs"):
            import os
            from auth import configure_astroquery_auth

            logger.info(f"=== AUTH DEBUG for {module_name} ===")
            logger.info(f"API_DEV_KEY env var present: {bool(os.environ.get('API_DEV_KEY'))}")
            if os.environ.get('API_DEV_KEY'):
                logger.info(f"API_DEV_KEY length: {len(os.environ.get('API_DEV_KEY'))}")

            auth_status = configure_astroquery_auth()
            logger.info(f"Auth configuration result: {auth_status}")
            logger.info(f"=== END AUTH DEBUG ===")

        # Get the class/instance
        cls = get_class_instance(module_name)

        # Get the method
        method = getattr(cls, function_name, None)
        if method is None:
            raise MCPError(
                code=ErrorCode.VALIDATION_ERROR,
                message=f"Function not found: {module_name}.{function_name}",
                service="executor",
                recoverable=False,
                suggestion=f"Use list_functions to see available functions",
            )

        # Prepare arguments
        prepared_params = {}
        for key, value in params.items():
            prepared_params[key] = prepare_argument(value, key)

        logger.info(f"Executing {module_name}.{function_name} with {list(prepared_params.keys())}")

        # Execute the function
        result = method(**prepared_params)

        # Serialize the result
        serialized = serialize_result(result)

        return {
            "success": True,
            "module": module_name,
            "function": function_name,
            "params": {k: str(v)[:100] for k, v in params.items()},  # Truncate for logging
            "result": serialized,
        }

    except MCPError:
        raise
    except TypeError as e:
        # Usually means wrong parameters
        raise MCPError(
            code=ErrorCode.VALIDATION_ERROR,
            message=f"Invalid parameters for {module_name}.{function_name}: {e}",
            service="executor",
            recoverable=False,
            suggestion="Check parameter names and types using get_function_info",
            details={"params": list(params.keys())},
        )
    except Exception as e:
        raise MCPError(
            code=ErrorCode.SERVICE_ERROR,
            message=f"Execution failed: {e}",
            service=module_name,
            recoverable=True,
            suggestion="Check parameters and try again",
            details={"function": function_name, "error": str(e)},
        )


def list_modules() -> dict[str, Any]:
    """List available astroquery modules.

    Returns:
        Dict with module information.
    """
    modules = []
    for name, path in ASTROQUERY_MODULES.items():
        try:
            # Check if importable
            get_class_instance(name)
            available = True
        except Exception:
            available = False

        modules.append({
            "name": name,
            "class_path": path,
            "available": available,
        })

    return {
        "module_count": len(modules),
        "modules": modules,
    }


def list_functions(module_name: str | None = None) -> dict[str, Any]:
    """List available functions.

    Args:
        module_name: Optional module to filter by

    Returns:
        Dict with function information.
    """
    all_funcs = discover_all_functions()

    if module_name:
        if module_name not in all_funcs:
            return {"functions": [], "error": f"Module not found: {module_name}"}
        funcs = all_funcs[module_name]
    else:
        funcs = []
        for module_funcs in all_funcs.values():
            funcs.extend(module_funcs)

    # Convert to serializable format
    function_list = []
    for f in funcs:
        function_list.append({
            "name": f.full_name,
            "module": f.module_name,
            "method": f.method_name,
            "description": f.description[:200] if f.description else "",
            "parameters": [
                {
                    "name": p.name,
                    "type": p.type_hint,
                    "required": not p.has_default,
                    "default": str(p.default)[:50] if p.has_default else None,
                    "description": p.description,
                }
                for p in f.parameters
            ],
        })

    return {
        "function_count": len(function_list),
        "functions": function_list,
    }


def get_function_info(module_name: str, function_name: str) -> dict[str, Any]:
    """Get detailed info about a specific function.

    Args:
        module_name: Module name
        function_name: Function name

    Returns:
        Detailed function information.
    """
    all_funcs = discover_all_functions()

    if module_name not in all_funcs:
        return {"error": f"Module not found: {module_name}"}

    for f in all_funcs[module_name]:
        if f.method_name == function_name:
            return {
                "name": f.full_name,
                "module": f.module_name,
                "class": f.class_name,
                "method": f.method_name,
                "description": f.description,
                "parameters": [
                    {
                        "name": p.name,
                        "type": p.type_hint,
                        "required": not p.has_default,
                        "default": str(p.default) if p.has_default else None,
                        "description": p.description,
                    }
                    for p in f.parameters
                ],
            }

    return {"error": f"Function not found: {module_name}.{function_name}"}
