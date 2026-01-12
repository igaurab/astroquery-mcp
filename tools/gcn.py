"""GCN alerts tools."""

import re
from typing import Any

from http_client import fetch_json, fetch_text
from models.errors import MCPError, ErrorCode


# GCN API base URL
GCN_API_BASE = "https://gcn.nasa.gov/api"
GCN_CIRCULARS_API = "https://gcn.nasa.gov/circulars"


async def fetch_circular(circular_id: int) -> dict[str, Any]:
    """Fetch a GCN Circular by ID.

    Args:
        circular_id: Circular ID number

    Returns:
        Alert event with circular content.
    """
    try:
        # Fetch circular from GCN
        url = f"{GCN_CIRCULARS_API}/{circular_id}.json"

        data = await fetch_json(url)

        # Parse the circular
        return {
            "success": True,
            "service": "gcn",
            "event_id": str(circular_id),
            "event_type": "GCN_CIRCULAR",
            "circular_id": circular_id,
            "subject": data.get("subject", ""),
            "submitter": data.get("submitter", ""),
            "submitted_at": data.get("createdAt", ""),
            "body": data.get("body", ""),
            "url": f"https://gcn.nasa.gov/circulars/{circular_id}",
        }

    except MCPError:
        raise
    except Exception as e:
        raise MCPError(
            code=ErrorCode.SERVICE_ERROR,
            message=f"Failed to fetch circular: {str(e)}",
            service="gcn",
            recoverable=True,
            suggestion="Check circular ID",
            details={"circular_id": circular_id, "error": str(e)},
        )


async def search_circulars(
    query: str,
    event_name: str | None = None,
    limit: int = 50,
) -> dict[str, Any]:
    """Search GCN circulars.

    Args:
        query: Search query
        event_name: Specific event name to filter
        limit: Maximum results

    Returns:
        List of matching circulars.
    """
    try:
        # Build search URL
        search_query = query
        if event_name:
            search_query = f"{event_name} {query}"

        # GCN search API
        url = f"{GCN_CIRCULARS_API}?query={search_query}&limit={limit}"

        data = await fetch_json(url)

        circulars = []
        items = data if isinstance(data, list) else data.get("items", [])

        for item in items[:limit]:
            circular = {
                "circular_id": item.get("circularId"),
                "subject": item.get("subject", ""),
                "submitter": item.get("submitter", ""),
                "submitted_at": item.get("createdAt", ""),
                "url": f"https://gcn.nasa.gov/circulars/{item.get('circularId')}",
            }
            circulars.append(circular)

        return {
            "success": True,
            "service": "gcn",
            "query": {"search": query, "event_name": event_name},
            "total_count": len(circulars),
            "returned_count": len(circulars),
            "data": circulars,
        }

    except MCPError:
        raise
    except Exception as e:
        raise MCPError(
            code=ErrorCode.SERVICE_ERROR,
            message=f"Circular search failed: {str(e)}",
            service="gcn",
            recoverable=True,
            suggestion="Try different search terms",
            details={"query": query, "error": str(e)},
        )


async def fetch_notice(notice_id: str, notice_type: str | None = None) -> dict[str, Any]:
    """Fetch a GCN Notice.

    Args:
        notice_id: Notice ID
        notice_type: Notice type filter

    Returns:
        Alert event with notice content.
    """
    try:
        # GCN notices are typically in the Kafka stream
        # For now, return notice metadata
        url = f"{GCN_API_BASE}/notices/{notice_id}"

        try:
            data = await fetch_json(url)
        except Exception:
            # If API fails, construct from ID
            data = {"id": notice_id}

        return {
            "success": True,
            "service": "gcn",
            "event_id": notice_id,
            "event_type": notice_type or "GCN_NOTICE",
            "notice_id": notice_id,
            "data": data,
            "url": f"https://gcn.nasa.gov/notices/{notice_id}",
        }

    except MCPError:
        raise
    except Exception as e:
        raise MCPError(
            code=ErrorCode.SERVICE_ERROR,
            message=f"Failed to fetch notice: {str(e)}",
            service="gcn",
            recoverable=True,
            suggestion="Check notice ID",
            details={"notice_id": notice_id, "error": str(e)},
        )


def parse_localization(content: str) -> dict[str, Any]:
    """Extract localization from alert content.

    Args:
        content: Alert text or JSON content

    Returns:
        Localization with coordinates and error.
    """
    result = {
        "success": True,
        "service": "gcn",
        "localization": None,
        "warnings": [],
    }

    # Try to parse as JSON first
    import json

    try:
        data = json.loads(content)
        if isinstance(data, dict):
            # Look for standard fields
            if "ra" in data and "dec" in data:
                result["localization"] = {
                    "ra": float(data["ra"]),
                    "dec": float(data["dec"]),
                    "error_radius": float(data.get("error", data.get("error_radius", 0.1))),
                    "source": "json",
                }
                return result
    except (json.JSONDecodeError, TypeError):
        pass

    # Parse text content for coordinates
    # Common patterns in GCN circulars

    # Pattern: RA, Dec (J2000) = 12h 34m 56.7s, +12d 34' 56.7"
    pattern1 = r"RA[,\s]+Dec[^=]*=\s*(\d+h\s*\d+m\s*[\d.]+s)[,\s]+([+-]?\d+d\s*\d+['\u2019]\s*[\d.]+[\"\u201d]?)"
    match = re.search(pattern1, content, re.IGNORECASE)
    if match:
        from astropy.coordinates import SkyCoord
        from astropy import units as u

        try:
            ra_str = match.group(1)
            dec_str = match.group(2).replace("'", "'").replace('"', '"')
            coord = SkyCoord(ra_str, dec_str, unit=(u.hourangle, u.deg))
            result["localization"] = {
                "ra": coord.ra.deg,
                "dec": coord.dec.deg,
                "error_radius": 0.1,  # Default
                "source": "text_hms",
            }
            return result
        except Exception as e:
            result["warnings"].append(f"Failed to parse HMS coordinates: {e}")

    # Pattern: RA = 123.456, Dec = -12.345
    pattern2 = r"RA\s*[=:]\s*([\d.]+)[^\d]*Dec\s*[=:]\s*([+-]?[\d.]+)"
    match = re.search(pattern2, content, re.IGNORECASE)
    if match:
        try:
            ra = float(match.group(1))
            dec = float(match.group(2))
            if 0 <= ra <= 360 and -90 <= dec <= 90:
                result["localization"] = {
                    "ra": ra,
                    "dec": dec,
                    "error_radius": 0.1,
                    "source": "text_deg",
                }
                return result
        except ValueError as e:
            result["warnings"].append(f"Failed to parse degree coordinates: {e}")

    # Pattern: error radius/box
    error_pattern = r"error[^:]*[:=]\s*([\d.]+)\s*(deg|arcmin|arcsec)?"
    error_match = re.search(error_pattern, content, re.IGNORECASE)
    if error_match and result["localization"]:
        error_val = float(error_match.group(1))
        unit = error_match.group(2) or "deg"
        if unit.lower() == "arcmin":
            error_val /= 60
        elif unit.lower() == "arcsec":
            error_val /= 3600
        result["localization"]["error_radius"] = error_val

    if result["localization"] is None:
        result["warnings"].append("No coordinates found in content")

    return result


async def crossmatch_vo(localization: dict) -> dict[str, Any]:
    """Run VO queries over a GCN localization.

    Args:
        localization: Localization dict with ra, dec, error_radius

    Returns:
        Crossmatched sources.
    """
    from tools.simbad import query_region as simbad_query_region

    if not localization:
        raise MCPError(
            code=ErrorCode.VALIDATION_ERROR,
            message="Localization required",
            service="gcn",
            recoverable=False,
            suggestion="Use gcn_parse_localization first",
            details={},
        )

    ra = localization.get("ra")
    dec = localization.get("dec")
    error_radius = localization.get("error_radius", 0.1)

    if ra is None or dec is None:
        raise MCPError(
            code=ErrorCode.VALIDATION_ERROR,
            message="Localization must contain ra and dec",
            service="gcn",
            recoverable=False,
            suggestion="Provide localization with ra, dec, and optionally error_radius",
            details={"localization": localization},
        )

    # Query SIMBAD for objects in error region
    # Convert error_radius from degrees to arcmin
    radius_arcmin = error_radius * 60

    try:
        simbad_result = simbad_query_region(
            ra=ra,
            dec=dec,
            radius=radius_arcmin,
            radius_unit="arcmin",
            limit=100,
        )

        return {
            "success": True,
            "service": "gcn",
            "localization": localization,
            "crossmatch": {
                "simbad": simbad_result,
            },
        }

    except Exception as e:
        return {
            "success": False,
            "service": "gcn",
            "localization": localization,
            "error": str(e),
            "crossmatch": {},
        }
