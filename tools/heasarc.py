"""HEASARC archive tools."""

from typing import Any

from astropy import units as u
from astropy.coordinates import SkyCoord

from config import get_config
from models.errors import MCPError, ErrorCode
from retry import run_sync_with_retry
from utils.coord_utils import validate_coordinates
from utils.table_utils import table_to_records


def list_catalogs(master: bool = True) -> dict[str, Any]:
    """List available HEASARC catalogs.

    Args:
        master: List from master catalog

    Returns:
        List of catalogs.
    """
    try:
        from astroquery.heasarc import Heasarc

        # Get catalog list
        catalogs = run_sync_with_retry(
            Heasarc.query_mission_list,
            service="heasarc",
        )

        if catalogs is None:
            return {
                "success": True,
                "service": "heasarc",
                "catalog_count": 0,
                "catalogs": [],
            }

        records = table_to_records(catalogs)

        return {
            "success": True,
            "service": "heasarc",
            "catalog_count": len(records),
            "catalogs": records,
        }

    except Exception as e:
        raise MCPError(
            code=ErrorCode.SERVICE_ERROR,
            message=f"Failed to list HEASARC catalogs: {str(e)}",
            service="heasarc",
            recoverable=True,
            suggestion="Try again later",
            details={"error": str(e)},
        )


def list_columns(catalog: str) -> dict[str, Any]:
    """Get columns for a HEASARC catalog.

    Args:
        catalog: Catalog name

    Returns:
        Column definitions.
    """
    try:
        from astroquery.heasarc import Heasarc

        columns = run_sync_with_retry(
            Heasarc.query_mission_cols,
            mission=catalog,
            service="heasarc",
        )

        if columns is None:
            raise MCPError(
                code=ErrorCode.CATALOG_NOT_FOUND,
                message=f"Catalog not found: {catalog}",
                service="heasarc",
                recoverable=False,
                suggestion="Use heasarc_list_catalogs to see available catalogs",
                details={"catalog": catalog},
            )

        records = table_to_records(columns)

        return {
            "success": True,
            "service": "heasarc",
            "catalog": catalog,
            "column_count": len(records),
            "columns": records,
        }

    except MCPError:
        raise
    except Exception as e:
        raise MCPError(
            code=ErrorCode.SERVICE_ERROR,
            message=f"Failed to get columns: {str(e)}",
            service="heasarc",
            recoverable=True,
            suggestion="Check catalog name",
            details={"catalog": catalog, "error": str(e)},
        )


def query_region(
    catalog: str,
    ra: float,
    dec: float,
    radius: float,
    columns: list[str] | None = None,
) -> dict[str, Any]:
    """Query a HEASARC catalog by position.

    Args:
        catalog: Catalog name
        ra: Right ascension in degrees
        dec: Declination in degrees
        radius: Search radius in arcmin
        columns: Columns to return

    Returns:
        Search results.
    """
    from astroquery.heasarc import Heasarc

    validate_coordinates(ra, dec)

    coord = SkyCoord(ra=ra * u.deg, dec=dec * u.deg, frame="icrs")

    try:
        kwargs = {
            "mission": catalog,
            "position": coord,
            "radius": radius * u.arcmin,
        }

        if columns:
            kwargs["fields"] = ",".join(columns)

        result = run_sync_with_retry(
            Heasarc.query_region,
            service="heasarc",
            **kwargs,
        )

        if result is None or len(result) == 0:
            return {
                "success": True,
                "service": "heasarc",
                "query": {"catalog": catalog, "ra": ra, "dec": dec, "radius": radius},
                "total_count": 0,
                "returned_count": 0,
                "data": [],
            }

        records = table_to_records(result)

        # Add archive field
        for record in records:
            record["archive"] = "HEASARC"
            record["catalog"] = catalog

        return {
            "success": True,
            "service": "heasarc",
            "query": {"catalog": catalog, "ra": ra, "dec": dec, "radius": radius},
            "total_count": len(records),
            "returned_count": len(records),
            "data": records,
        }

    except MCPError:
        raise
    except Exception as e:
        raise MCPError(
            code=ErrorCode.SERVICE_ERROR,
            message=f"HEASARC query failed: {str(e)}",
            service="heasarc",
            recoverable=True,
            suggestion="Check catalog name and coordinates",
            details={"catalog": catalog, "ra": ra, "dec": dec, "error": str(e)},
        )


def query_tap(query: str) -> dict[str, Any]:
    """Execute ADQL query on HEASARC TAP.

    Args:
        query: ADQL query

    Returns:
        Query results.
    """
    from tools.vo import tap_query

    return tap_query("heasarc", query)


def get_data_links(obsid: str, catalog: str) -> dict[str, Any]:
    """Get data download links for an observation.

    Args:
        obsid: Observation ID
        catalog: Catalog name

    Returns:
        Download URLs.
    """
    # HEASARC data links typically follow patterns
    base_url = "https://heasarc.gsfc.nasa.gov/FTP"

    # Common download URL patterns by mission
    links = {
        "obsid": obsid,
        "catalog": catalog,
        "browse_url": f"https://heasarc.gsfc.nasa.gov/cgi-bin/W3Browse/w3query.pl?tablehead={catalog}&Entry={obsid}",
    }

    # Add FTP link for common missions
    if catalog.lower().startswith("xmm"):
        links["data_url"] = f"{base_url}/xmm/data/rev0/{obsid}"
    elif catalog.lower().startswith("chandra"):
        links["data_url"] = f"https://cda.harvard.edu/chaser/startViewer.do?obsid={obsid}"
    elif catalog.lower().startswith("swift"):
        links["data_url"] = f"{base_url}/swift/data/obs"
    elif catalog.lower().startswith("fermi"):
        links["data_url"] = f"https://fermi.gsfc.nasa.gov/cgi-bin/ssc/LAT/LATDataQuery.cgi"

    return {
        "success": True,
        "service": "heasarc",
        "obsid": obsid,
        "catalog": catalog,
        "links": links,
    }
