"""Discovery tools for orchestrating agent."""

from typing import Any

from models.results import ServiceInfo, ToolSignature, ToolParameter

# Service definitions
SERVICES: dict[str, ServiceInfo] = {
    "ads": ServiceInfo(
        name="ads",
        description="NASA Astrophysics Data System - literature search and bibliographic data",
        category="literature",
        requires_auth=True,
        tools=[
            "ads_search_papers",
            "ads_get_record",
            "ads_get_links",
            "ads_get_fulltext",
        ],
    ),
    "simbad": ServiceInfo(
        name="simbad",
        description="SIMBAD astronomical database - object resolution and crossmatch",
        category="resolver",
        requires_auth=False,
        tools=[
            "simbad_resolve_name",
            "simbad_query_region",
            "simbad_get_object_info",
        ],
    ),
    "vo": ServiceInfo(
        name="vo",
        description="Virtual Observatory protocols - TAP, SIA, SSA queries",
        category="vo",
        requires_auth=False,
        tools=[
            "vo_tap_query",
            "vo_tap_list_tables",
            "vo_tap_table_schema",
            "vo_sia_search",
            "vo_ssa_search",
            "vo_discover_services",
        ],
    ),
    "heasarc": ServiceInfo(
        name="heasarc",
        description="HEASARC - High Energy Astrophysics archive",
        category="archive",
        requires_auth=False,
        tools=[
            "heasarc_list_catalogs",
            "heasarc_list_columns",
            "heasarc_query_region",
            "heasarc_query_tap",
            "heasarc_get_data_links",
        ],
    ),
    "irsa": ServiceInfo(
        name="irsa",
        description="IRSA - Infrared Science Archive",
        category="archive",
        requires_auth=False,
        tools=[
            "irsa_list_catalogs",
            "irsa_query_region",
            "irsa_get_images",
        ],
    ),
    "mast": ServiceInfo(
        name="mast",
        description="MAST - Mikulski Archive for Space Telescopes",
        category="archive",
        requires_auth=False,
        tools=[
            "mast_query_region",
            "mast_query_criteria",
            "mast_get_product_list",
            "mast_get_download_urls",
            "mast_catalog_query",
        ],
    ),
    "nea": ServiceInfo(
        name="nea",
        description="NASA Exoplanet Archive - exoplanet data",
        category="archive",
        requires_auth=False,
        tools=[
            "nea_query_criteria",
            "nea_query_object",
            "nea_query_region",
            "nea_list_tables",
        ],
    ),
    "gcn": ServiceInfo(
        name="gcn",
        description="GCN - Gamma-ray Coordinates Network alerts",
        category="alerts",
        requires_auth=False,
        tools=[
            "gcn_fetch_circular",
            "gcn_search_circulars",
            "gcn_fetch_notice",
            "gcn_parse_localization",
            "gcn_crossmatch_vo",
        ],
    ),
}

# Tool signatures
TOOL_SIGNATURES: dict[str, ToolSignature] = {
    # ADS tools
    "ads_search_papers": ToolSignature(
        name="ads_search_papers",
        description="Search ADS for papers matching a query",
        service="ads",
        parameters=[
            ToolParameter(
                name="query",
                type="str",
                description="ADS search query (e.g., 'gravitational waves year:2020')",
                required=True,
            ),
            ToolParameter(
                name="page",
                type="int",
                description="Page number (1-indexed)",
                required=False,
                default=1,
            ),
            ToolParameter(
                name="rows_per_page",
                type="int",
                description="Results per page (max 1000)",
                required=False,
                default=100,
            ),
            ToolParameter(
                name="sort",
                type="str",
                description="Sort order (e.g., 'date desc', 'citation_count desc')",
                required=False,
                default="date desc",
            ),
            ToolParameter(
                name="fields",
                type="list[str]",
                description="Fields to return",
                required=False,
                default=None,
            ),
        ],
        returns="SearchResult with list of PaperResult records",
        example="ads_search_papers(query='exoplanet atmospheres', rows_per_page=50)",
    ),
    "ads_get_record": ToolSignature(
        name="ads_get_record",
        description="Get a single paper by bibcode",
        service="ads",
        parameters=[
            ToolParameter(
                name="bibcode",
                type="str",
                description="ADS bibcode (e.g., '2020ApJ...900..100X')",
                required=True,
            ),
            ToolParameter(
                name="fields",
                type="list[str]",
                description="Fields to return",
                required=False,
                default=None,
            ),
        ],
        returns="PaperResult with paper metadata",
        example="ads_get_record(bibcode='2020ApJ...900..100X')",
    ),
    "ads_get_links": ToolSignature(
        name="ads_get_links",
        description="Get available links (PDF, data, etc.) for a paper",
        service="ads",
        parameters=[
            ToolParameter(
                name="bibcode",
                type="str",
                description="ADS bibcode",
                required=True,
            ),
            ToolParameter(
                name="link_type",
                type="str",
                description="Specific link type to filter (e.g., 'pdf', 'data')",
                required=False,
                default=None,
            ),
        ],
        returns="Dict mapping link types to URLs",
        example="ads_get_links(bibcode='2020ApJ...900..100X', link_type='pdf')",
    ),
    "ads_get_fulltext": ToolSignature(
        name="ads_get_fulltext",
        description="Get full text of a paper (tries ADS first, then publisher)",
        service="ads",
        parameters=[
            ToolParameter(
                name="bibcode",
                type="str",
                description="ADS bibcode",
                required=True,
            ),
            ToolParameter(
                name="prefer_format",
                type="str",
                description="Preferred format ('pdf' or 'html')",
                required=False,
                default="pdf",
            ),
        ],
        returns="Dict with URL to full text or content if available",
        example="ads_get_fulltext(bibcode='2020ApJ...900..100X')",
    ),
    # SIMBAD tools
    "simbad_resolve_name": ToolSignature(
        name="simbad_resolve_name",
        description="Resolve an astronomical object name to coordinates",
        service="simbad",
        parameters=[
            ToolParameter(
                name="name",
                type="str",
                description="Object name (e.g., 'M31', 'Vega', 'NGC 4993')",
                required=True,
            ),
            ToolParameter(
                name="include_ids",
                type="bool",
                description="Include alternative identifiers",
                required=False,
                default=False,
            ),
        ],
        returns="ObjectInfo with coordinates and metadata",
        example="simbad_resolve_name(name='M31', include_ids=True)",
    ),
    "simbad_query_region": ToolSignature(
        name="simbad_query_region",
        description="Query objects within a region around coordinates",
        service="simbad",
        parameters=[
            ToolParameter(
                name="ra",
                type="float",
                description="Right ascension in degrees",
                required=True,
            ),
            ToolParameter(
                name="dec",
                type="float",
                description="Declination in degrees",
                required=True,
            ),
            ToolParameter(
                name="radius",
                type="float",
                description="Search radius",
                required=True,
            ),
            ToolParameter(
                name="radius_unit",
                type="str",
                description="Radius unit ('arcmin', 'arcsec', 'deg')",
                required=False,
                default="arcmin",
            ),
            ToolParameter(
                name="limit",
                type="int",
                description="Maximum results to return",
                required=False,
                default=100,
            ),
        ],
        returns="SearchResult with list of ObjectInfo records",
        example="simbad_query_region(ra=10.68, dec=41.27, radius=5, radius_unit='arcmin')",
    ),
    "simbad_get_object_info": ToolSignature(
        name="simbad_get_object_info",
        description="Get detailed information about an object",
        service="simbad",
        parameters=[
            ToolParameter(
                name="name",
                type="str",
                description="Object name",
                required=True,
            ),
            ToolParameter(
                name="fields",
                type="list[str]",
                description="Specific fields to query",
                required=False,
                default=None,
            ),
        ],
        returns="ObjectInfo with detailed metadata",
        example="simbad_get_object_info(name='M31')",
    ),
    # VO tools
    "vo_tap_query": ToolSignature(
        name="vo_tap_query",
        description="Execute an ADQL query against a TAP service",
        service="vo",
        parameters=[
            ToolParameter(
                name="service_url",
                type="str",
                description="TAP service URL (or alias from config)",
                required=True,
            ),
            ToolParameter(
                name="query",
                type="str",
                description="ADQL query",
                required=True,
            ),
            ToolParameter(
                name="async_mode",
                type="bool",
                description="Use async mode for large queries",
                required=False,
                default=False,
            ),
            ToolParameter(
                name="max_rows",
                type="int",
                description="Maximum rows to return",
                required=False,
                default=10000,
            ),
        ],
        returns="SearchResult with query results",
        example="vo_tap_query(service_url='gaia', query='SELECT TOP 10 * FROM gaiadr3.gaia_source')",
    ),
    "vo_tap_list_tables": ToolSignature(
        name="vo_tap_list_tables",
        description="List tables available at a TAP service",
        service="vo",
        parameters=[
            ToolParameter(
                name="service_url",
                type="str",
                description="TAP service URL (or alias from config)",
                required=True,
            ),
        ],
        returns="List of table names and descriptions",
        example="vo_tap_list_tables(service_url='vizier')",
    ),
    "vo_tap_table_schema": ToolSignature(
        name="vo_tap_table_schema",
        description="Get schema for a TAP table",
        service="vo",
        parameters=[
            ToolParameter(
                name="service_url",
                type="str",
                description="TAP service URL",
                required=True,
            ),
            ToolParameter(
                name="table_name",
                type="str",
                description="Table name",
                required=True,
            ),
        ],
        returns="Table schema with column definitions",
        example="vo_tap_table_schema(service_url='gaia', table_name='gaiadr3.gaia_source')",
    ),
    "vo_sia_search": ToolSignature(
        name="vo_sia_search",
        description="Search for images using Simple Image Access",
        service="vo",
        parameters=[
            ToolParameter(
                name="service_url",
                type="str",
                description="SIA service URL",
                required=True,
            ),
            ToolParameter(
                name="ra",
                type="float",
                description="Right ascension in degrees",
                required=True,
            ),
            ToolParameter(
                name="dec",
                type="float",
                description="Declination in degrees",
                required=True,
            ),
            ToolParameter(
                name="radius",
                type="float",
                description="Search radius in degrees",
                required=True,
            ),
            ToolParameter(
                name="format",
                type="str",
                description="Image format filter",
                required=False,
                default=None,
            ),
        ],
        returns="SearchResult with image access URLs",
        example="vo_sia_search(service_url='irsa', ra=10.68, dec=41.27, radius=0.1)",
    ),
    "vo_ssa_search": ToolSignature(
        name="vo_ssa_search",
        description="Search for spectra using Simple Spectral Access",
        service="vo",
        parameters=[
            ToolParameter(
                name="service_url",
                type="str",
                description="SSA service URL",
                required=True,
            ),
            ToolParameter(
                name="ra",
                type="float",
                description="Right ascension in degrees",
                required=True,
            ),
            ToolParameter(
                name="dec",
                type="float",
                description="Declination in degrees",
                required=True,
            ),
            ToolParameter(
                name="radius",
                type="float",
                description="Search radius in degrees",
                required=True,
            ),
            ToolParameter(
                name="band",
                type="tuple",
                description="Wavelength range (min, max) in meters",
                required=False,
                default=None,
            ),
        ],
        returns="SearchResult with spectra access URLs",
        example="vo_ssa_search(service_url='esa', ra=10.68, dec=41.27, radius=0.1)",
    ),
    "vo_discover_services": ToolSignature(
        name="vo_discover_services",
        description="Discover VO services for a given resource type",
        service="vo",
        parameters=[
            ToolParameter(
                name="resource_type",
                type="str",
                description="Service type ('tap', 'sia', 'ssa', 'cone')",
                required=True,
            ),
            ToolParameter(
                name="keywords",
                type="str",
                description="Search keywords",
                required=False,
                default=None,
            ),
        ],
        returns="List of VOResource objects",
        example="vo_discover_services(resource_type='tap', keywords='x-ray')",
    ),
    # HEASARC tools
    "heasarc_list_catalogs": ToolSignature(
        name="heasarc_list_catalogs",
        description="List available HEASARC catalogs",
        service="heasarc",
        parameters=[
            ToolParameter(
                name="master",
                type="bool",
                description="List from master catalog",
                required=False,
                default=True,
            ),
        ],
        returns="List of catalog names and descriptions",
        example="heasarc_list_catalogs()",
    ),
    "heasarc_list_columns": ToolSignature(
        name="heasarc_list_columns",
        description="Get columns for a HEASARC catalog",
        service="heasarc",
        parameters=[
            ToolParameter(
                name="catalog",
                type="str",
                description="Catalog name",
                required=True,
            ),
        ],
        returns="List of column definitions",
        example="heasarc_list_columns(catalog='xmmssc')",
    ),
    "heasarc_query_region": ToolSignature(
        name="heasarc_query_region",
        description="Query a HEASARC catalog by position",
        service="heasarc",
        parameters=[
            ToolParameter(
                name="catalog",
                type="str",
                description="Catalog name",
                required=True,
            ),
            ToolParameter(
                name="ra",
                type="float",
                description="Right ascension in degrees",
                required=True,
            ),
            ToolParameter(
                name="dec",
                type="float",
                description="Declination in degrees",
                required=True,
            ),
            ToolParameter(
                name="radius",
                type="float",
                description="Search radius in arcmin",
                required=True,
            ),
            ToolParameter(
                name="columns",
                type="list[str]",
                description="Columns to return",
                required=False,
                default=None,
            ),
        ],
        returns="SearchResult with catalog records",
        example="heasarc_query_region(catalog='xmmssc', ra=10.68, dec=41.27, radius=10)",
    ),
    "heasarc_query_tap": ToolSignature(
        name="heasarc_query_tap",
        description="Execute ADQL query on HEASARC TAP",
        service="heasarc",
        parameters=[
            ToolParameter(
                name="query",
                type="str",
                description="ADQL query",
                required=True,
            ),
        ],
        returns="SearchResult with query results",
        example="heasarc_query_tap(query='SELECT TOP 10 * FROM xmmssc')",
    ),
    "heasarc_get_data_links": ToolSignature(
        name="heasarc_get_data_links",
        description="Get data download links for observations",
        service="heasarc",
        parameters=[
            ToolParameter(
                name="obsid",
                type="str",
                description="Observation ID",
                required=True,
            ),
            ToolParameter(
                name="catalog",
                type="str",
                description="Catalog name",
                required=True,
            ),
        ],
        returns="Dict with download URLs",
        example="heasarc_get_data_links(obsid='0123456789', catalog='xmmssc')",
    ),
    # IRSA tools
    "irsa_list_catalogs": ToolSignature(
        name="irsa_list_catalogs",
        description="List available IRSA catalogs",
        service="irsa",
        parameters=[
            ToolParameter(
                name="filter",
                type="str",
                description="Filter catalogs by keyword",
                required=False,
                default=None,
            ),
        ],
        returns="List of catalog names and descriptions",
        example="irsa_list_catalogs(filter='wise')",
    ),
    "irsa_query_region": ToolSignature(
        name="irsa_query_region",
        description="Query an IRSA catalog by position",
        service="irsa",
        parameters=[
            ToolParameter(
                name="catalog",
                type="str",
                description="Catalog name",
                required=True,
            ),
            ToolParameter(
                name="ra",
                type="float",
                description="Right ascension in degrees",
                required=True,
            ),
            ToolParameter(
                name="dec",
                type="float",
                description="Declination in degrees",
                required=True,
            ),
            ToolParameter(
                name="radius",
                type="float",
                description="Search radius in arcmin",
                required=True,
            ),
            ToolParameter(
                name="columns",
                type="list[str]",
                description="Columns to return",
                required=False,
                default=None,
            ),
        ],
        returns="SearchResult with catalog records",
        example="irsa_query_region(catalog='wise_allsky_4band_p3as_psd', ra=10.68, dec=41.27, radius=5)",
    ),
    "irsa_get_images": ToolSignature(
        name="irsa_get_images",
        description="Search for images at a position",
        service="irsa",
        parameters=[
            ToolParameter(
                name="mission",
                type="str",
                description="Mission name (e.g., 'wise', '2mass')",
                required=True,
            ),
            ToolParameter(
                name="ra",
                type="float",
                description="Right ascension in degrees",
                required=True,
            ),
            ToolParameter(
                name="dec",
                type="float",
                description="Declination in degrees",
                required=True,
            ),
            ToolParameter(
                name="radius",
                type="float",
                description="Search radius in arcmin",
                required=True,
            ),
        ],
        returns="SearchResult with image URLs",
        example="irsa_get_images(mission='wise', ra=10.68, dec=41.27, radius=5)",
    ),
    # MAST tools
    "mast_query_region": ToolSignature(
        name="mast_query_region",
        description="Query MAST observations by position",
        service="mast",
        parameters=[
            ToolParameter(
                name="ra",
                type="float",
                description="Right ascension in degrees",
                required=True,
            ),
            ToolParameter(
                name="dec",
                type="float",
                description="Declination in degrees",
                required=True,
            ),
            ToolParameter(
                name="radius",
                type="float",
                description="Search radius in arcmin",
                required=True,
            ),
        ],
        returns="SearchResult with observation records",
        example="mast_query_region(ra=10.68, dec=41.27, radius=5)",
    ),
    "mast_query_criteria": ToolSignature(
        name="mast_query_criteria",
        description="Query MAST observations by criteria",
        service="mast",
        parameters=[
            ToolParameter(
                name="obs_collection",
                type="str",
                description="Observation collection (e.g., 'HST', 'JWST')",
                required=False,
                default=None,
            ),
            ToolParameter(
                name="instrument_name",
                type="str",
                description="Instrument name",
                required=False,
                default=None,
            ),
            ToolParameter(
                name="proposal_pi",
                type="str",
                description="PI name",
                required=False,
                default=None,
            ),
            ToolParameter(
                name="target_name",
                type="str",
                description="Target name",
                required=False,
                default=None,
            ),
        ],
        returns="SearchResult with observation records",
        example="mast_query_criteria(obs_collection='JWST', target_name='M31')",
    ),
    "mast_get_product_list": ToolSignature(
        name="mast_get_product_list",
        description="Get data products for observations",
        service="mast",
        parameters=[
            ToolParameter(
                name="obs_ids",
                type="list[str]",
                description="Observation IDs",
                required=True,
            ),
        ],
        returns="List of data products with URLs",
        example="mast_get_product_list(obs_ids=['jw01234001001'])",
    ),
    "mast_get_download_urls": ToolSignature(
        name="mast_get_download_urls",
        description="Get download URLs for data products",
        service="mast",
        parameters=[
            ToolParameter(
                name="product_list",
                type="list",
                description="List of products from mast_get_product_list",
                required=True,
            ),
            ToolParameter(
                name="mrp_only",
                type="bool",
                description="Only minimum recommended products",
                required=False,
                default=False,
            ),
        ],
        returns="List of download URLs",
        example="mast_get_download_urls(product_list=products, mrp_only=True)",
    ),
    "mast_catalog_query": ToolSignature(
        name="mast_catalog_query",
        description="Query a MAST catalog",
        service="mast",
        parameters=[
            ToolParameter(
                name="catalog",
                type="str",
                description="Catalog name",
                required=True,
            ),
            ToolParameter(
                name="ra",
                type="float",
                description="Right ascension in degrees",
                required=True,
            ),
            ToolParameter(
                name="dec",
                type="float",
                description="Declination in degrees",
                required=True,
            ),
            ToolParameter(
                name="radius",
                type="float",
                description="Search radius in arcmin",
                required=True,
            ),
        ],
        returns="SearchResult with catalog records",
        example="mast_catalog_query(catalog='HSC', ra=10.68, dec=41.27, radius=5)",
    ),
    # NEA tools
    "nea_query_criteria": ToolSignature(
        name="nea_query_criteria",
        description="Query NASA Exoplanet Archive with criteria",
        service="nea",
        parameters=[
            ToolParameter(
                name="table",
                type="str",
                description="Table name (e.g., 'ps', 'pscomppars')",
                required=True,
            ),
            ToolParameter(
                name="select",
                type="str",
                description="Columns to select",
                required=False,
                default="*",
            ),
            ToolParameter(
                name="where",
                type="str",
                description="WHERE clause",
                required=False,
                default=None,
            ),
            ToolParameter(
                name="order",
                type="str",
                description="ORDER BY clause",
                required=False,
                default=None,
            ),
        ],
        returns="SearchResult with exoplanet records",
        example="nea_query_criteria(table='ps', where='pl_bmassj > 1', order='pl_bmassj desc')",
    ),
    "nea_query_object": ToolSignature(
        name="nea_query_object",
        description="Query for a specific planet or host star",
        service="nea",
        parameters=[
            ToolParameter(
                name="object_name",
                type="str",
                description="Object name (e.g., 'TRAPPIST-1 b')",
                required=True,
            ),
            ToolParameter(
                name="table",
                type="str",
                description="Table name",
                required=False,
                default="ps",
            ),
        ],
        returns="SearchResult with object data",
        example="nea_query_object(object_name='TRAPPIST-1 b')",
    ),
    "nea_query_region": ToolSignature(
        name="nea_query_region",
        description="Query exoplanets by position",
        service="nea",
        parameters=[
            ToolParameter(
                name="ra",
                type="float",
                description="Right ascension in degrees",
                required=True,
            ),
            ToolParameter(
                name="dec",
                type="float",
                description="Declination in degrees",
                required=True,
            ),
            ToolParameter(
                name="radius",
                type="float",
                description="Search radius in degrees",
                required=True,
            ),
            ToolParameter(
                name="table",
                type="str",
                description="Table name",
                required=False,
                default="ps",
            ),
        ],
        returns="SearchResult with exoplanet records",
        example="nea_query_region(ra=10.68, dec=41.27, radius=1)",
    ),
    "nea_list_tables": ToolSignature(
        name="nea_list_tables",
        description="List available NEA tables",
        service="nea",
        parameters=[],
        returns="List of table names and descriptions",
        example="nea_list_tables()",
    ),
    # GCN tools
    "gcn_fetch_circular": ToolSignature(
        name="gcn_fetch_circular",
        description="Fetch a GCN Circular by ID",
        service="gcn",
        parameters=[
            ToolParameter(
                name="circular_id",
                type="int",
                description="Circular ID number",
                required=True,
            ),
        ],
        returns="AlertEvent with circular content",
        example="gcn_fetch_circular(circular_id=12345)",
    ),
    "gcn_search_circulars": ToolSignature(
        name="gcn_search_circulars",
        description="Search GCN circulars by keyword or event",
        service="gcn",
        parameters=[
            ToolParameter(
                name="query",
                type="str",
                description="Search query",
                required=True,
            ),
            ToolParameter(
                name="event_name",
                type="str",
                description="Specific event name to filter",
                required=False,
                default=None,
            ),
            ToolParameter(
                name="limit",
                type="int",
                description="Maximum results",
                required=False,
                default=50,
            ),
        ],
        returns="List of AlertEvent objects",
        example="gcn_search_circulars(query='GRB', limit=20)",
    ),
    "gcn_fetch_notice": ToolSignature(
        name="gcn_fetch_notice",
        description="Fetch a GCN Notice",
        service="gcn",
        parameters=[
            ToolParameter(
                name="notice_id",
                type="str",
                description="Notice ID",
                required=True,
            ),
            ToolParameter(
                name="notice_type",
                type="str",
                description="Notice type filter",
                required=False,
                default=None,
            ),
        ],
        returns="AlertEvent with notice content",
        example="gcn_fetch_notice(notice_id='FERMI_GBM_FLT_POS_1234567890')",
    ),
    "gcn_parse_localization": ToolSignature(
        name="gcn_parse_localization",
        description="Extract localization from alert content",
        service="gcn",
        parameters=[
            ToolParameter(
                name="content",
                type="str",
                description="Alert text or JSON content",
                required=True,
            ),
        ],
        returns="Dict with ra, dec, error_radius or sky region",
        example="gcn_parse_localization(content='...')",
    ),
    "gcn_crossmatch_vo": ToolSignature(
        name="gcn_crossmatch_vo",
        description="Run VO queries over a GCN localization",
        service="gcn",
        parameters=[
            ToolParameter(
                name="localization",
                type="dict",
                description="Localization from gcn_parse_localization",
                required=True,
            ),
        ],
        returns="SearchResult with crossmatched sources",
        example="gcn_crossmatch_vo(localization={'ra': 10.0, 'dec': 20.0, 'error_radius': 0.5})",
    ),
}


def list_services(category: str | None = None) -> list[dict[str, Any]]:
    """List available astronomical services.

    Args:
        category: Optional category filter (literature, resolver, archive, vo, alerts)

    Returns:
        List of service info dictionaries.
    """
    services = list(SERVICES.values())

    if category:
        services = [s for s in services if s.category == category]

    return [s.model_dump() for s in services]


def get_function_signatures(service: str) -> list[dict[str, Any]]:
    """Get detailed function signatures for a service's tools.

    Args:
        service: Service name (e.g., 'ads', 'simbad')

    Returns:
        List of tool signature dictionaries.
    """
    if service not in SERVICES:
        return []

    service_info = SERVICES[service]
    signatures = []

    for tool_name in service_info.tools:
        if tool_name in TOOL_SIGNATURES:
            sig = TOOL_SIGNATURES[tool_name]
            signatures.append(sig.model_dump())

    return signatures


def get_service_status(service: str) -> dict[str, Any]:
    """Check status of a service.

    Args:
        service: Service name

    Returns:
        Status dictionary with availability info.
    """
    from auth import check_auth_status

    if service not in SERVICES:
        return {"available": False, "error": f"Unknown service: {service}"}

    service_info = SERVICES[service]
    auth_status = check_auth_status()

    result = {
        "service": service,
        "available": True,
        "category": service_info.category,
        "requires_auth": service_info.requires_auth,
    }

    if service_info.requires_auth:
        if service in auth_status:
            result["auth_configured"] = auth_status[service]["configured"]
            if not result["auth_configured"]:
                result["auth_env_var"] = auth_status[service]["env_var"]
                result["available"] = False
                result["error"] = f"Missing authentication token"

    return result
