"""Coordinate parsing and formatting utilities."""

from typing import Any

from astropy import units as u
from astropy.coordinates import SkyCoord

from models.errors import MCPError, ErrorCode


def parse_coordinates(
    ra: float | str,
    dec: float | str,
    frame: str = "icrs",
) -> SkyCoord:
    """Parse coordinates into a SkyCoord object.

    Args:
        ra: Right ascension in degrees (float) or sexagesimal string.
        dec: Declination in degrees (float) or sexagesimal string.
        frame: Coordinate frame (default: 'icrs').

    Returns:
        SkyCoord object.

    Raises:
        MCPError: If coordinates cannot be parsed.
    """
    try:
        # If both are numeric, treat as degrees
        if isinstance(ra, (int, float)) and isinstance(dec, (int, float)):
            return SkyCoord(ra=ra * u.deg, dec=dec * u.deg, frame=frame)

        # Try to parse as strings (sexagesimal or degrees)
        return SkyCoord(ra, dec, unit=(u.hourangle, u.deg), frame=frame)

    except Exception as e:
        raise MCPError(
            code=ErrorCode.INVALID_COORDINATES,
            message=f"Cannot parse coordinates: ra={ra}, dec={dec}",
            service="coordinates",
            recoverable=False,
            suggestion="Provide RA in degrees (0-360) and Dec in degrees (-90 to 90)",
            details={"ra": str(ra), "dec": str(dec), "error": str(e)},
        )


def parse_coordinates_flexible(
    target: str | None = None,
    ra: float | None = None,
    dec: float | None = None,
    frame: str = "icrs",
) -> SkyCoord:
    """Parse coordinates from either a target name or RA/Dec values.

    Args:
        target: Object name to resolve (e.g., "M31").
        ra: Right ascension in degrees.
        dec: Declination in degrees.
        frame: Coordinate frame.

    Returns:
        SkyCoord object.

    Raises:
        MCPError: If coordinates cannot be determined.
    """
    if target:
        try:
            return SkyCoord.from_name(target, frame=frame)
        except Exception as e:
            raise MCPError(
                code=ErrorCode.OBJECT_NOT_FOUND,
                message=f"Cannot resolve target name: {target}",
                service="coordinates",
                recoverable=False,
                suggestion="Provide explicit RA/Dec coordinates or check the object name",
                details={"target": target, "error": str(e)},
            )

    if ra is not None and dec is not None:
        return parse_coordinates(ra, dec, frame)

    raise MCPError(
        code=ErrorCode.MISSING_PARAMETER,
        message="Either target name or RA/Dec coordinates must be provided",
        service="coordinates",
        recoverable=False,
        suggestion="Provide either 'target' (object name) or both 'ra' and 'dec' parameters",
        details={},
    )


def format_coordinates(coord: SkyCoord) -> dict[str, Any]:
    """Format a SkyCoord object as a dictionary.

    Args:
        coord: SkyCoord object to format.

    Returns:
        Dictionary with coordinate information.
    """
    return {
        "ra_deg": coord.ra.deg,
        "dec_deg": coord.dec.deg,
        "ra_hms": coord.ra.to_string(unit=u.hourangle, sep=":", precision=2),
        "dec_dms": coord.dec.to_string(unit=u.deg, sep=":", precision=1),
        "galactic_l": coord.galactic.l.deg,
        "galactic_b": coord.galactic.b.deg,
        "frame": coord.frame.name,
    }


def angular_separation(
    ra1: float,
    dec1: float,
    ra2: float,
    dec2: float,
) -> float:
    """Calculate angular separation between two points in degrees.

    Args:
        ra1, dec1: First position in degrees.
        ra2, dec2: Second position in degrees.

    Returns:
        Angular separation in degrees.
    """
    c1 = SkyCoord(ra=ra1 * u.deg, dec=dec1 * u.deg)
    c2 = SkyCoord(ra=ra2 * u.deg, dec=dec2 * u.deg)
    return c1.separation(c2).deg


def validate_coordinates(ra: float, dec: float) -> bool:
    """Validate that coordinates are within valid ranges.

    Args:
        ra: Right ascension in degrees.
        dec: Declination in degrees.

    Returns:
        True if valid.

    Raises:
        MCPError: If coordinates are out of range.
    """
    if not (0 <= ra < 360):
        raise MCPError(
            code=ErrorCode.INVALID_COORDINATES,
            message=f"RA must be between 0 and 360 degrees, got {ra}",
            service="coordinates",
            recoverable=False,
            suggestion="Provide RA in degrees (0-360)",
            details={"ra": ra},
        )

    if not (-90 <= dec <= 90):
        raise MCPError(
            code=ErrorCode.INVALID_COORDINATES,
            message=f"Dec must be between -90 and 90 degrees, got {dec}",
            service="coordinates",
            recoverable=False,
            suggestion="Provide Dec in degrees (-90 to 90)",
            details={"dec": dec},
        )

    return True
