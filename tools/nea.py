"""NASA Exoplanet Archive tools."""

from typing import Any

from astroquery_mcp.models.errors import MCPError, ErrorCode
from astroquery_mcp.retry import run_sync_with_retry
from astroquery_mcp.utils.coord_utils import validate_coordinates
from astroquery_mcp.utils.table_utils import table_to_records


# Available NEA tables
NEA_TABLES = {
    "ps": "Planetary Systems - default planet parameters",
    "pscomppars": "Planetary Systems Composite Parameters",
    "keplernames": "Kepler Objects of Interest names",
    "k2names": "K2 Objects of Interest names",
    "toinames": "TESS Objects of Interest names",
    "stellarhosts": "Stellar hosts of confirmed planets",
    "transitspec": "Transit Spectroscopy measurements",
    "emissionspec": "Emission Spectroscopy measurements",
}


def list_tables() -> dict[str, Any]:
    """List available NEA tables.

    Returns:
        List of tables with descriptions.
    """
    tables = [{"name": k, "description": v} for k, v in NEA_TABLES.items()]

    return {
        "success": True,
        "service": "nea",
        "table_count": len(tables),
        "tables": tables,
    }


def query_criteria(
    table: str,
    select: str = "*",
    where: str | None = None,
    order: str | None = None,
) -> dict[str, Any]:
    """Query NEA with criteria.

    Args:
        table: Table name
        select: Columns to select
        where: WHERE clause
        order: ORDER BY clause

    Returns:
        Query results.
    """
    from astroquery.ipac.nexsci.nasa_exoplanet_archive import NasaExoplanetArchive

    if table not in NEA_TABLES:
        raise MCPError(
            code=ErrorCode.VALIDATION_ERROR,
            message=f"Unknown table: {table}",
            service="nea",
            recoverable=False,
            suggestion=f"Use one of: {', '.join(NEA_TABLES.keys())}",
            details={"table": table, "available": list(NEA_TABLES.keys())},
        )

    try:
        kwargs = {"table": table}

        if select and select != "*":
            kwargs["select"] = select

        if where:
            kwargs["where"] = where

        if order:
            kwargs["order"] = order

        result = run_sync_with_retry(
            NasaExoplanetArchive.query_criteria,
            service="nea",
            **kwargs,
        )

        if result is None or len(result) == 0:
            return {
                "success": True,
                "service": "nea",
                "query": {"table": table, "select": select, "where": where, "order": order},
                "total_count": 0,
                "returned_count": 0,
                "data": [],
            }

        records = table_to_records(result)

        return {
            "success": True,
            "service": "nea",
            "query": {"table": table, "select": select, "where": where, "order": order},
            "total_count": len(records),
            "returned_count": len(records),
            "data": records,
        }

    except MCPError:
        raise
    except Exception as e:
        raise MCPError(
            code=ErrorCode.SERVICE_ERROR,
            message=f"NEA query failed: {str(e)}",
            service="nea",
            recoverable=True,
            suggestion="Check query syntax",
            details={"table": table, "where": where, "error": str(e)},
        )


def query_object(object_name: str, table: str = "ps") -> dict[str, Any]:
    """Query for a specific planet or host.

    Args:
        object_name: Object name (e.g., 'TRAPPIST-1 b')
        table: Table name

    Returns:
        Object data.
    """
    from astroquery.ipac.nexsci.nasa_exoplanet_archive import NasaExoplanetArchive

    try:
        result = run_sync_with_retry(
            NasaExoplanetArchive.query_object,
            object_name,
            table=table,
            service="nea",
        )

        if result is None or len(result) == 0:
            raise MCPError(
                code=ErrorCode.OBJECT_NOT_FOUND,
                message=f"Object not found: {object_name}",
                service="nea",
                recoverable=False,
                suggestion="Check the object name or search with different criteria",
                details={"object_name": object_name, "table": table},
            )

        records = table_to_records(result)

        return {
            "success": True,
            "service": "nea",
            "object_name": object_name,
            "table": table,
            "result_count": len(records),
            "data": records,
        }

    except MCPError:
        raise
    except Exception as e:
        raise MCPError(
            code=ErrorCode.SERVICE_ERROR,
            message=f"NEA query failed: {str(e)}",
            service="nea",
            recoverable=True,
            suggestion="Check object name",
            details={"object_name": object_name, "error": str(e)},
        )


def query_region(
    ra: float,
    dec: float,
    radius: float,
    table: str = "ps",
) -> dict[str, Any]:
    """Query exoplanets by position.

    Args:
        ra: Right ascension in degrees
        dec: Declination in degrees
        radius: Search radius in degrees
        table: Table name

    Returns:
        Exoplanet records.
    """
    from astropy import units as u
    from astropy.coordinates import SkyCoord
    from astroquery.ipac.nexsci.nasa_exoplanet_archive import NasaExoplanetArchive

    validate_coordinates(ra, dec)

    coord = SkyCoord(ra=ra * u.deg, dec=dec * u.deg, frame="icrs")

    try:
        result = run_sync_with_retry(
            NasaExoplanetArchive.query_region,
            table=table,
            coordinates=coord,
            radius=radius * u.deg,
            service="nea",
        )

        if result is None or len(result) == 0:
            return {
                "success": True,
                "service": "nea",
                "query": {"table": table, "ra": ra, "dec": dec, "radius": radius},
                "total_count": 0,
                "returned_count": 0,
                "data": [],
            }

        records = table_to_records(result)

        return {
            "success": True,
            "service": "nea",
            "query": {"table": table, "ra": ra, "dec": dec, "radius": radius},
            "total_count": len(records),
            "returned_count": len(records),
            "data": records,
        }

    except MCPError:
        raise
    except Exception as e:
        raise MCPError(
            code=ErrorCode.SERVICE_ERROR,
            message=f"NEA region query failed: {str(e)}",
            service="nea",
            recoverable=True,
            suggestion="Check coordinates and radius",
            details={"ra": ra, "dec": dec, "radius": radius, "error": str(e)},
        )
