"""Result models for astroquery MCP server."""

from typing import Any

from pydantic import BaseModel, Field


class ServiceInfo(BaseModel):
    """Information about an available service."""

    name: str = Field(description="Service identifier")
    description: str = Field(description="Human-readable description")
    category: str = Field(
        description="Service category (literature, resolver, archive, vo, alerts)"
    )
    requires_auth: bool = Field(default=False, description="Whether auth is required")
    tools: list[str] = Field(
        default_factory=list, description="List of tool names for this service"
    )


class ToolParameter(BaseModel):
    """Parameter definition for a tool."""

    name: str
    type: str
    description: str
    required: bool = True
    default: Any = None


class ToolSignature(BaseModel):
    """Detailed signature for a tool."""

    name: str = Field(description="Tool name")
    description: str = Field(description="Tool description")
    service: str = Field(description="Parent service")
    parameters: list[ToolParameter] = Field(
        default_factory=list, description="Tool parameters"
    )
    returns: str = Field(description="Description of return value")
    example: str | None = Field(default=None, description="Example usage")


class CoordinateResult(BaseModel):
    """Result containing coordinate information."""

    ra_deg: float = Field(description="Right ascension in degrees")
    dec_deg: float = Field(description="Declination in degrees")
    ra_hms: str | None = Field(default=None, description="RA in HMS format")
    dec_dms: str | None = Field(default=None, description="Dec in DMS format")
    galactic_l: float | None = Field(default=None, description="Galactic longitude")
    galactic_b: float | None = Field(default=None, description="Galactic latitude")
    frame: str = Field(default="icrs", description="Coordinate frame")


class ObjectInfo(BaseModel):
    """Information about an astronomical object."""

    name: str = Field(description="Object name")
    main_id: str | None = Field(default=None, description="Main identifier")
    coordinates: CoordinateResult | None = Field(default=None)
    object_type: str | None = Field(default=None, description="Object type (e.g., Galaxy)")
    identifiers: list[str] = Field(
        default_factory=list, description="Alternative identifiers"
    )
    distance: float | None = Field(default=None, description="Distance in parsecs")
    redshift: float | None = Field(default=None, description="Redshift")
    radial_velocity: float | None = Field(
        default=None, description="Radial velocity in km/s"
    )
    morphological_type: str | None = Field(
        default=None, description="Morphological classification"
    )


class PaperResult(BaseModel):
    """Result for a paper/publication."""

    bibcode: str = Field(description="ADS bibcode")
    title: str = Field(description="Paper title")
    authors: list[str] = Field(default_factory=list, description="Author list")
    abstract: str | None = Field(default=None, description="Abstract text")
    pub_date: str | None = Field(default=None, description="Publication date")
    journal: str | None = Field(default=None, description="Journal name")
    doi: str | None = Field(default=None, description="DOI if available")
    citation_count: int | None = Field(default=None, description="Citation count")
    keywords: list[str] = Field(default_factory=list, description="Keywords")
    links: dict[str, str] = Field(
        default_factory=dict, description="Available links (pdf, data, etc.)"
    )


class ArchiveRecord(BaseModel):
    """Record from an astronomical archive."""

    archive: str = Field(description="Archive name (HEASARC, IRSA, MAST, NEA)")
    dataset_id: str = Field(description="Dataset/observation ID")
    ra: float | None = Field(default=None, description="RA in degrees")
    dec: float | None = Field(default=None, description="Dec in degrees")
    time_start: str | None = Field(default=None, description="Observation start time")
    time_end: str | None = Field(default=None, description="Observation end time")
    bandpass: str | None = Field(default=None, description="Bandpass/filter")
    wavelength_min: float | None = Field(default=None, description="Min wavelength (nm)")
    wavelength_max: float | None = Field(default=None, description="Max wavelength (nm)")
    product_type: str | None = Field(
        default=None, description="Product type (image, spectrum, etc.)"
    )
    access_url: str | None = Field(default=None, description="Data access URL")
    file_size: int | None = Field(default=None, description="File size in bytes")
    proprietary: bool = Field(default=False, description="Is data proprietary?")
    proprietary_period_end: str | None = Field(
        default=None, description="When proprietary period ends"
    )
    instrument: str | None = Field(default=None, description="Instrument name")
    telescope: str | None = Field(default=None, description="Telescope name")
    target_name: str | None = Field(default=None, description="Target name if available")
    additional_fields: dict[str, Any] = Field(
        default_factory=dict, description="Archive-specific fields"
    )


class VOResource(BaseModel):
    """Virtual Observatory resource/service."""

    ivoid: str = Field(description="IVOA identifier")
    short_name: str = Field(description="Short name")
    title: str = Field(description="Resource title")
    description: str | None = Field(default=None)
    service_type: str = Field(description="Service type (tap, sia, ssa, etc.)")
    access_url: str = Field(description="Service access URL")
    publisher: str | None = Field(default=None, description="Resource publisher")


class AlertEvent(BaseModel):
    """Astronomical alert/transient event."""

    event_id: str = Field(description="Event identifier")
    event_type: str = Field(description="Event type (GRB, GW, neutrino, etc.)")
    trigger_time: str | None = Field(default=None, description="Trigger time (ISO format)")
    ra: float | None = Field(default=None, description="Best estimate RA (deg)")
    dec: float | None = Field(default=None, description="Best estimate Dec (deg)")
    error_radius: float | None = Field(default=None, description="Error radius (deg)")
    source: str = Field(description="Alert source (GCN, TNS, etc.)")
    circular_id: str | None = Field(default=None, description="GCN circular ID")
    notice_type: str | None = Field(default=None, description="Notice type")
    significance: float | None = Field(default=None, description="Detection significance")
    url: str | None = Field(default=None, description="Link to more information")
    raw_text: str | None = Field(default=None, description="Raw alert text")


class SearchResult(BaseModel):
    """Generic search result container."""

    success: bool = Field(default=True)
    service: str = Field(description="Service that returned this result")
    query: dict[str, Any] = Field(
        default_factory=dict, description="Query parameters used"
    )
    total_count: int | None = Field(
        default=None, description="Total matching results (if known)"
    )
    returned_count: int = Field(default=0, description="Number of results returned")
    data: list[dict[str, Any]] = Field(
        default_factory=list, description="Result records"
    )
    warnings: list[str] = Field(
        default_factory=list, description="Any warnings generated"
    )
    truncated: bool = Field(
        default=False, description="Whether results were truncated"
    )
