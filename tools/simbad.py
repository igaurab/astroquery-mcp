"""SIMBAD object resolution tools."""

from typing import Any

from astropy import units as u
from astropy.coordinates import SkyCoord

from astroquery_mcp.config import get_config
from astroquery_mcp.models.errors import MCPError, ErrorCode
from astroquery_mcp.retry import run_sync_with_retry, get_rate_limiter
from astroquery_mcp.utils.coord_utils import format_coordinates, validate_coordinates
from astroquery_mcp.utils.table_utils import table_to_records


def _get_simbad_instance():
    """Get configured Simbad instance."""
    from astroquery.simbad import Simbad

    simbad = Simbad()
    # Add useful fields (using new SIMBAD TAP column names)
    simbad.add_votable_fields("otype", "otypes", "ids", "distance", "morphtype")
    return simbad


def resolve_name(name: str, include_ids: bool = False) -> dict[str, Any]:
    """Resolve an astronomical object name to coordinates.

    Args:
        name: Object name (e.g., 'M31', 'Vega')
        include_ids: Include alternative identifiers

    Returns:
        Object info with coordinates.
    """
    config = get_config()

    # Try SIMBAD first
    try:
        simbad = _get_simbad_instance()

        result = run_sync_with_retry(
            simbad.query_object, name, service="simbad"
        )

        if result is None or len(result) == 0:
            # Try fallback resolvers
            return _resolve_with_fallback(name, config.simbad.resolvers.fallback_order)

        row = result[0]

        # Extract coordinates (handle both old uppercase and new lowercase column names)
        # New SIMBAD TAP uses lowercase 'ra', 'dec' in degrees
        ra_col = "ra" if "ra" in row.colnames else "RA"
        dec_col = "dec" if "dec" in row.colnames else "DEC"

        # Check if coordinates are in degrees (new) or hourangle (old)
        if "ra" in row.colnames:
            # New format: already in degrees
            coord = SkyCoord(
                ra=row[ra_col] * u.deg, dec=row[dec_col] * u.deg, frame="icrs"
            )
        else:
            # Old format: RA in hourangle
            coord = SkyCoord(
                ra=row[ra_col], dec=row[dec_col], unit=(u.hourangle, u.deg), frame="icrs"
            )

        # Get main_id (handle case variations)
        main_id_col = next((c for c in row.colnames if c.lower() == "main_id"), None)
        main_id = str(row[main_id_col]) if main_id_col else name

        # Get object type (handle case variations)
        otype_col = next((c for c in row.colnames if c.lower() == "otype"), None)
        object_type = str(row[otype_col]) if otype_col and row[otype_col] else None

        response = {
            "name": name,
            "main_id": main_id,
            "coordinates": format_coordinates(coord),
            "object_type": object_type,
        }

        # Add optional fields (handle both old and new column names)
        for dist_col in ["Distance_distance", "distance_distance", "dist"]:
            if dist_col in row.colnames:
                try:
                    val = row[dist_col]
                    if val is not None and not (hasattr(val, 'mask') and val.mask):
                        response["distance_pc"] = float(val)
                        break
                except (ValueError, TypeError):
                    pass

        for morph_col in ["MORPHTYPE", "morphtype", "morph_type"]:
            if morph_col in row.colnames:
                try:
                    val = row[morph_col]
                    if val is not None and str(val).strip():
                        response["morphological_type"] = str(val)
                        break
                except (ValueError, TypeError):
                    pass

        # Get identifiers if requested
        if include_ids:
            ids_result = run_sync_with_retry(
                simbad.query_objectids, name, service="simbad"
            )
            if ids_result is not None:
                # Handle both old ('ID') and new ('id') column names
                id_col = "id" if "id" in ids_result.colnames else "ID"
                response["identifiers"] = [str(row[id_col]) for row in ids_result]

        return response

    except MCPError:
        raise
    except Exception as e:
        raise MCPError(
            code=ErrorCode.SERVICE_ERROR,
            message=f"SIMBAD query failed: {str(e)}",
            service="simbad",
            recoverable=True,
            suggestion="Try again or use alternative resolver",
            details={"name": name, "error": str(e)},
        )


def _resolve_with_fallback(name: str, fallback_order: list[str]) -> dict[str, Any]:
    """Try to resolve with fallback resolvers."""
    errors = []

    for resolver in fallback_order:
        if resolver == "simbad":
            continue  # Already tried

        try:
            if resolver == "ned":
                return _resolve_with_ned(name)
            elif resolver == "vizier":
                return _resolve_with_vizier(name)
        except Exception as e:
            errors.append((resolver, str(e)))
            continue

    raise MCPError(
        code=ErrorCode.OBJECT_NOT_FOUND,
        message=f"Object '{name}' not found in any resolver",
        service="simbad",
        recoverable=False,
        suggestion="Check the object name or provide coordinates directly",
        details={"name": name, "tried_resolvers": errors},
    )


def _resolve_with_ned(name: str) -> dict[str, Any]:
    """Resolve using NED."""
    from astroquery.ipac.ned import Ned

    result = run_sync_with_retry(Ned.query_object, name, service="ned")

    if result is None or len(result) == 0:
        raise MCPError(
            code=ErrorCode.OBJECT_NOT_FOUND,
            message=f"Object '{name}' not found in NED",
            service="ned",
            recoverable=False,
            suggestion="Try a different name",
            details={"name": name},
        )

    row = result[0]
    coord = SkyCoord(ra=row["RA"], dec=row["DEC"], unit=(u.deg, u.deg), frame="icrs")

    return {
        "name": name,
        "main_id": str(row["Object Name"]) if "Object Name" in row.colnames else name,
        "coordinates": format_coordinates(coord),
        "object_type": str(row["Type"]) if "Type" in row.colnames else None,
        "resolver": "ned",
    }


def _resolve_with_vizier(name: str) -> dict[str, Any]:
    """Resolve using Vizier/Sesame."""
    # Use SkyCoord's name resolver which uses Sesame
    try:
        coord = SkyCoord.from_name(name)
        return {
            "name": name,
            "main_id": name,
            "coordinates": format_coordinates(coord),
            "resolver": "sesame",
        }
    except Exception as e:
        raise MCPError(
            code=ErrorCode.OBJECT_NOT_FOUND,
            message=f"Object '{name}' not found via Sesame",
            service="vizier",
            recoverable=False,
            suggestion="Check the object name",
            details={"name": name, "error": str(e)},
        )


def query_region(
    ra: float,
    dec: float,
    radius: float,
    radius_unit: str = "arcmin",
    limit: int = 100,
) -> dict[str, Any]:
    """Query objects within a region.

    Args:
        ra: Right ascension in degrees
        dec: Declination in degrees
        radius: Search radius
        radius_unit: Unit for radius
        limit: Maximum results

    Returns:
        Search results with objects.
    """
    validate_coordinates(ra, dec)

    # Convert radius unit
    unit_map = {"arcmin": u.arcmin, "arcsec": u.arcsec, "deg": u.deg}
    if radius_unit not in unit_map:
        raise MCPError(
            code=ErrorCode.VALIDATION_ERROR,
            message=f"Invalid radius unit: {radius_unit}",
            service="simbad",
            recoverable=False,
            suggestion="Use 'arcmin', 'arcsec', or 'deg'",
            details={"radius_unit": radius_unit},
        )

    coord = SkyCoord(ra=ra * u.deg, dec=dec * u.deg, frame="icrs")
    search_radius = radius * unit_map[radius_unit]

    try:
        simbad = _get_simbad_instance()
        config = get_config()

        # Apply row limit
        simbad.ROW_LIMIT = min(limit, config.simbad.row_limit)

        result = run_sync_with_retry(
            simbad.query_region, coord, radius=search_radius, service="simbad"
        )

        if result is None or len(result) == 0:
            return {
                "success": True,
                "service": "simbad",
                "query": {"ra": ra, "dec": dec, "radius": radius, "unit": radius_unit},
                "total_count": 0,
                "returned_count": 0,
                "data": [],
            }

        # Convert to records
        records = table_to_records(result)

        # Enhance records with parsed coordinates
        for record in records:
            if "RA" in record and "DEC" in record:
                try:
                    obj_coord = SkyCoord(
                        ra=record["RA"],
                        dec=record["DEC"],
                        unit=(u.hourangle, u.deg),
                        frame="icrs",
                    )
                    record["ra_deg"] = obj_coord.ra.deg
                    record["dec_deg"] = obj_coord.dec.deg
                    record["separation_arcmin"] = coord.separation(obj_coord).arcmin
                except Exception:
                    pass

        # Sort by separation
        records.sort(key=lambda x: x.get("separation_arcmin", float("inf")))

        return {
            "success": True,
            "service": "simbad",
            "query": {"ra": ra, "dec": dec, "radius": radius, "unit": radius_unit},
            "total_count": len(records),
            "returned_count": len(records),
            "data": records,
        }

    except MCPError:
        raise
    except Exception as e:
        raise MCPError(
            code=ErrorCode.SERVICE_ERROR,
            message=f"SIMBAD region query failed: {str(e)}",
            service="simbad",
            recoverable=True,
            suggestion="Try again with a smaller radius",
            details={"ra": ra, "dec": dec, "radius": radius, "error": str(e)},
        )


def get_object_info(name: str, fields: list[str] | None = None) -> dict[str, Any]:
    """Get detailed information about an object.

    Args:
        name: Object name
        fields: Specific fields to query

    Returns:
        Detailed object information.
    """
    # First resolve to get basic info
    basic_info = resolve_name(name, include_ids=True)

    try:
        simbad = _get_simbad_instance()

        # Add extra fields if specified
        if fields:
            for field in fields:
                try:
                    simbad.add_votable_fields(field)
                except Exception:
                    pass

        # Query for full info
        result = run_sync_with_retry(simbad.query_object, name, service="simbad")

        if result is not None and len(result) > 0:
            row = result[0]
            records = table_to_records(result)
            if records:
                # Merge with basic info
                basic_info["details"] = records[0]

        # Get measurements if available
        try:
            measurements = run_sync_with_retry(
                simbad.query_objectids, name, service="simbad"
            )
            if measurements is not None:
                basic_info["measurement_count"] = len(measurements)
        except Exception:
            pass

        return basic_info

    except MCPError:
        raise
    except Exception as e:
        # Return basic info even if detailed query fails
        basic_info["warning"] = f"Could not fetch detailed info: {str(e)}"
        return basic_info
