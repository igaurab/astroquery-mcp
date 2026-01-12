"""IRSA archive tools."""

from typing import Any

from astropy import units as u
from astropy.coordinates import SkyCoord

from astroquery_mcp.models.errors import MCPError, ErrorCode
from astroquery_mcp.retry import run_sync_with_retry
from astroquery_mcp.utils.coord_utils import validate_coordinates
from astroquery_mcp.utils.table_utils import table_to_records


def list_catalogs(filter: str | None = None) -> dict[str, Any]:
    """List available IRSA catalogs.

    Args:
        filter: Filter catalogs by keyword

    Returns:
        List of catalogs.
    """
    try:
        from astroquery.ipac.irsa import Irsa

        catalogs = run_sync_with_retry(
            Irsa.list_catalogs,
            service="irsa",
        )

        if catalogs is None:
            return {
                "success": True,
                "service": "irsa",
                "catalog_count": 0,
                "catalogs": [],
            }

        # Convert to list
        catalog_list = []
        for name, desc in catalogs.items():
            if filter and filter.lower() not in name.lower() and filter.lower() not in str(desc).lower():
                continue
            catalog_list.append({
                "name": name,
                "description": str(desc) if desc else "",
            })

        return {
            "success": True,
            "service": "irsa",
            "filter": filter,
            "catalog_count": len(catalog_list),
            "catalogs": catalog_list,
        }

    except Exception as e:
        raise MCPError(
            code=ErrorCode.SERVICE_ERROR,
            message=f"Failed to list IRSA catalogs: {str(e)}",
            service="irsa",
            recoverable=True,
            suggestion="Try again later",
            details={"filter": filter, "error": str(e)},
        )


def query_region(
    catalog: str,
    ra: float,
    dec: float,
    radius: float,
    columns: list[str] | None = None,
) -> dict[str, Any]:
    """Query an IRSA catalog by position.

    Args:
        catalog: Catalog name
        ra: Right ascension in degrees
        dec: Declination in degrees
        radius: Search radius in arcmin
        columns: Columns to return

    Returns:
        Search results.
    """
    from astroquery.ipac.irsa import Irsa

    validate_coordinates(ra, dec)

    coord = SkyCoord(ra=ra * u.deg, dec=dec * u.deg, frame="icrs")

    try:
        kwargs = {
            "catalog": catalog,
            "coordinates": coord,
            "radius": radius * u.arcmin,
        }

        if columns:
            kwargs["columns"] = columns

        result = run_sync_with_retry(
            Irsa.query_region,
            service="irsa",
            **kwargs,
        )

        if result is None or len(result) == 0:
            return {
                "success": True,
                "service": "irsa",
                "query": {"catalog": catalog, "ra": ra, "dec": dec, "radius": radius},
                "total_count": 0,
                "returned_count": 0,
                "data": [],
            }

        records = table_to_records(result)

        # Add archive field
        for record in records:
            record["archive"] = "IRSA"
            record["catalog"] = catalog

        return {
            "success": True,
            "service": "irsa",
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
            message=f"IRSA query failed: {str(e)}",
            service="irsa",
            recoverable=True,
            suggestion="Check catalog name and coordinates",
            details={"catalog": catalog, "ra": ra, "dec": dec, "error": str(e)},
        )


def get_images(
    mission: str,
    ra: float,
    dec: float,
    radius: float,
) -> dict[str, Any]:
    """Search for images at a position.

    Args:
        mission: Mission name (e.g., 'wise', '2mass')
        ra: Right ascension in degrees
        dec: Declination in degrees
        radius: Search radius in arcmin

    Returns:
        Image URLs.
    """
    validate_coordinates(ra, dec)

    coord = SkyCoord(ra=ra * u.deg, dec=dec * u.deg, frame="icrs")

    # Map mission names to IRSA image services
    mission_map = {
        "wise": "allwise",
        "2mass": "2mass",
        "spitzer": "seip",
        "iras": "iras",
    }

    mission_key = mission_map.get(mission.lower(), mission)

    try:
        # Try using IRSA's image query
        from astroquery.ipac.irsa import Irsa

        # For now, construct URLs to IRSA image services
        images = []

        # WISE images
        if "wise" in mission.lower() or "allwise" in mission.lower():
            for band in ["w1", "w2", "w3", "w4"]:
                images.append({
                    "mission": "WISE",
                    "band": band,
                    "access_url": f"https://irsa.ipac.caltech.edu/cgi-bin/Cutouts/nph-cutouts?mission=WISE&min_size=1&max_size=3600&units=arcsec&locstr={ra}+{dec}&mode=PI&ntable_cutouts=1&cutouttbl1=allwise-multiband&size={radius*60}",
                    "format": "fits",
                })

        # 2MASS images
        if "2mass" in mission.lower():
            for band in ["j", "h", "k"]:
                images.append({
                    "mission": "2MASS",
                    "band": band,
                    "access_url": f"https://irsa.ipac.caltech.edu/cgi-bin/Cutouts/nph-cutouts?mission=2MASS&min_size=1&max_size=3600&units=arcsec&locstr={ra}+{dec}&mode=PI&ntable_cutouts=1&size={radius*60}",
                    "format": "fits",
                })

        if not images:
            # Generic IRSA finder chart
            images.append({
                "mission": mission,
                "access_url": f"https://irsa.ipac.caltech.edu/cgi-bin/finder_chart/nph-finder?locstr={ra}+{dec}&survey={mission}&mode=PI",
                "format": "html",
            })

        return {
            "success": True,
            "service": "irsa",
            "query": {"mission": mission, "ra": ra, "dec": dec, "radius": radius},
            "total_count": len(images),
            "returned_count": len(images),
            "data": images,
        }

    except Exception as e:
        raise MCPError(
            code=ErrorCode.SERVICE_ERROR,
            message=f"IRSA image query failed: {str(e)}",
            service="irsa",
            recoverable=True,
            suggestion="Check mission name and coordinates",
            details={"mission": mission, "ra": ra, "dec": dec, "error": str(e)},
        )
