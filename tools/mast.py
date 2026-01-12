"""MAST archive tools."""

from typing import Any

from astropy import units as u
from astropy.coordinates import SkyCoord

from astroquery_mcp.models.errors import MCPError, ErrorCode
from astroquery_mcp.retry import run_sync_with_retry
from astroquery_mcp.utils.coord_utils import validate_coordinates
from astroquery_mcp.utils.table_utils import table_to_records


def query_region(ra: float, dec: float, radius: float) -> dict[str, Any]:
    """Query MAST observations by position.

    Args:
        ra: Right ascension in degrees
        dec: Declination in degrees
        radius: Search radius in arcmin

    Returns:
        Observation records.
    """
    from astroquery.mast import Observations

    validate_coordinates(ra, dec)

    coord = SkyCoord(ra=ra * u.deg, dec=dec * u.deg, frame="icrs")

    try:
        result = run_sync_with_retry(
            Observations.query_region,
            coord,
            radius=radius * u.arcmin,
            service="mast",
        )

        if result is None or len(result) == 0:
            return {
                "success": True,
                "service": "mast",
                "query": {"ra": ra, "dec": dec, "radius": radius},
                "total_count": 0,
                "returned_count": 0,
                "data": [],
            }

        records = table_to_records(result)

        # Enhance records with MAST-specific info
        for record in records:
            record["archive"] = "MAST"
            # Add proprietary flag
            if "dataRights" in record:
                record["proprietary"] = record["dataRights"] != "PUBLIC"
            else:
                record["proprietary"] = False

        return {
            "success": True,
            "service": "mast",
            "query": {"ra": ra, "dec": dec, "radius": radius},
            "total_count": len(records),
            "returned_count": len(records),
            "data": records,
        }

    except MCPError:
        raise
    except Exception as e:
        raise MCPError(
            code=ErrorCode.SERVICE_ERROR,
            message=f"MAST query failed: {str(e)}",
            service="mast",
            recoverable=True,
            suggestion="Check coordinates and try again",
            details={"ra": ra, "dec": dec, "error": str(e)},
        )


def query_criteria(
    obs_collection: str | None = None,
    instrument_name: str | None = None,
    proposal_pi: str | None = None,
    target_name: str | None = None,
) -> dict[str, Any]:
    """Query MAST observations by criteria.

    Args:
        obs_collection: Collection (HST, JWST, etc.)
        instrument_name: Instrument name
        proposal_pi: PI name
        target_name: Target name

    Returns:
        Observation records.
    """
    from astroquery.mast import Observations

    # Build criteria
    criteria = {}
    if obs_collection:
        criteria["obs_collection"] = obs_collection
    if instrument_name:
        criteria["instrument_name"] = instrument_name
    if proposal_pi:
        criteria["proposal_pi"] = proposal_pi
    if target_name:
        criteria["target_name"] = target_name

    if not criteria:
        raise MCPError(
            code=ErrorCode.VALIDATION_ERROR,
            message="At least one search criterion required",
            service="mast",
            recoverable=False,
            suggestion="Provide obs_collection, instrument_name, proposal_pi, or target_name",
            details={},
        )

    try:
        result = run_sync_with_retry(
            Observations.query_criteria,
            service="mast",
            **criteria,
        )

        if result is None or len(result) == 0:
            return {
                "success": True,
                "service": "mast",
                "query": criteria,
                "total_count": 0,
                "returned_count": 0,
                "data": [],
            }

        records = table_to_records(result)

        for record in records:
            record["archive"] = "MAST"
            if "dataRights" in record:
                record["proprietary"] = record["dataRights"] != "PUBLIC"

        return {
            "success": True,
            "service": "mast",
            "query": criteria,
            "total_count": len(records),
            "returned_count": len(records),
            "data": records,
        }

    except MCPError:
        raise
    except Exception as e:
        raise MCPError(
            code=ErrorCode.SERVICE_ERROR,
            message=f"MAST query failed: {str(e)}",
            service="mast",
            recoverable=True,
            suggestion="Check criteria values",
            details={"criteria": criteria, "error": str(e)},
        )


def get_product_list(obs_ids: list[str]) -> dict[str, Any]:
    """Get data products for observations.

    Args:
        obs_ids: List of observation IDs

    Returns:
        List of data products.
    """
    from astroquery.mast import Observations

    if not obs_ids:
        raise MCPError(
            code=ErrorCode.VALIDATION_ERROR,
            message="At least one observation ID required",
            service="mast",
            recoverable=False,
            suggestion="Provide obs_ids from query results",
            details={},
        )

    try:
        # First get observations by ID
        obs_table = run_sync_with_retry(
            Observations.query_criteria,
            obsid=obs_ids,
            service="mast",
        )

        if obs_table is None or len(obs_table) == 0:
            return {
                "success": True,
                "service": "mast",
                "obs_ids": obs_ids,
                "product_count": 0,
                "products": [],
            }

        # Get products
        products = run_sync_with_retry(
            Observations.get_product_list,
            obs_table,
            service="mast",
        )

        if products is None or len(products) == 0:
            return {
                "success": True,
                "service": "mast",
                "obs_ids": obs_ids,
                "product_count": 0,
                "products": [],
            }

        records = table_to_records(products)

        return {
            "success": True,
            "service": "mast",
            "obs_ids": obs_ids,
            "product_count": len(records),
            "products": records,
        }

    except MCPError:
        raise
    except Exception as e:
        raise MCPError(
            code=ErrorCode.SERVICE_ERROR,
            message=f"Failed to get products: {str(e)}",
            service="mast",
            recoverable=True,
            suggestion="Check observation IDs",
            details={"obs_ids": obs_ids, "error": str(e)},
        )


def get_download_urls(product_list: list, mrp_only: bool = False) -> dict[str, Any]:
    """Get download URLs for products.

    Args:
        product_list: Product records from get_product_list
        mrp_only: Only minimum recommended products

    Returns:
        Download URLs.
    """
    from astropy.table import Table
    from astroquery.mast import Observations

    if not product_list:
        return {
            "success": True,
            "service": "mast",
            "url_count": 0,
            "urls": [],
        }

    try:
        # Convert back to table if needed
        if isinstance(product_list, list):
            products = Table(rows=product_list)
        else:
            products = product_list

        # Filter if needed
        if mrp_only:
            products = Observations.filter_products(
                products,
                mrp_only=True,
            )

        # Get URLs (don't actually download)
        urls = []
        for row in products:
            url_info = {
                "product_filename": str(row.get("productFilename", "")),
                "product_type": str(row.get("productType", "")),
                "size": int(row.get("size", 0)) if row.get("size") else None,
            }

            # Build data URI
            if "dataURI" in row.colnames and row["dataURI"]:
                url_info["access_url"] = f"https://mast.stsci.edu/api/v0.1/Download/file?uri={row['dataURI']}"

            urls.append(url_info)

        return {
            "success": True,
            "service": "mast",
            "mrp_only": mrp_only,
            "url_count": len(urls),
            "urls": urls,
        }

    except Exception as e:
        raise MCPError(
            code=ErrorCode.SERVICE_ERROR,
            message=f"Failed to get download URLs: {str(e)}",
            service="mast",
            recoverable=True,
            suggestion="Check product list format",
            details={"error": str(e)},
        )


def catalog_query(
    catalog: str,
    ra: float,
    dec: float,
    radius: float,
) -> dict[str, Any]:
    """Query a MAST catalog.

    Args:
        catalog: Catalog name
        ra: Right ascension in degrees
        dec: Declination in degrees
        radius: Search radius in arcmin

    Returns:
        Catalog records.
    """
    from astroquery.mast import Catalogs

    validate_coordinates(ra, dec)

    coord = SkyCoord(ra=ra * u.deg, dec=dec * u.deg, frame="icrs")

    try:
        result = run_sync_with_retry(
            Catalogs.query_region,
            coord,
            radius=radius * u.arcmin,
            catalog=catalog,
            service="mast",
        )

        if result is None or len(result) == 0:
            return {
                "success": True,
                "service": "mast",
                "query": {"catalog": catalog, "ra": ra, "dec": dec, "radius": radius},
                "total_count": 0,
                "returned_count": 0,
                "data": [],
            }

        records = table_to_records(result)

        return {
            "success": True,
            "service": "mast",
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
            message=f"MAST catalog query failed: {str(e)}",
            service="mast",
            recoverable=True,
            suggestion="Check catalog name and coordinates",
            details={"catalog": catalog, "ra": ra, "dec": dec, "error": str(e)},
        )
