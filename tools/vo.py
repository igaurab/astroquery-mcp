"""Virtual Observatory (TAP, SIA, SSA) tools."""

from typing import Any

from config import get_config
from models.errors import MCPError, ErrorCode
from retry import run_sync_with_retry
from utils.table_utils import table_to_records
from utils.coord_utils import validate_coordinates


def _resolve_service_url(service_url: str, service_type: str = "tap") -> str:
    """Resolve a service alias to full URL.

    Args:
        service_url: URL or alias
        service_type: Type of service (tap, sia, ssa)

    Returns:
        Full service URL.
    """
    config = get_config()

    # If it's already a URL, return as-is
    if service_url.startswith("http"):
        return service_url

    # Look up in config
    endpoints = getattr(config.endpoints, service_type, {})
    if service_url in endpoints:
        return endpoints[service_url]

    # Common aliases
    aliases = {
        "gaia": "https://gea.esac.esa.int/tap-server/tap",
        "vizier": "http://tapvizier.u-strasbg.fr/TAPVizieR/tap",
        "heasarc": "https://heasarc.gsfc.nasa.gov/xamin/vo/tap",
        "irsa": "https://irsa.ipac.caltech.edu/TAP",
        "mast": "https://mast.stsci.edu/vo-tap/api/v0.1",
        "ned": "https://ned.ipac.caltech.edu/tap",
        "simbad": "http://simbad.u-strasbg.fr/simbad/sim-tap",
    }

    if service_url.lower() in aliases:
        return aliases[service_url.lower()]

    return service_url


def tap_query(
    service_url: str,
    query: str,
    async_mode: bool = False,
    max_rows: int = 10000,
) -> dict[str, Any]:
    """Execute a TAP/ADQL query.

    Args:
        service_url: TAP service URL or alias
        query: ADQL query
        async_mode: Use async mode for large queries
        max_rows: Maximum rows to return

    Returns:
        Query results.
    """
    import pyvo

    url = _resolve_service_url(service_url, "tap")

    try:
        service = pyvo.dal.TAPService(url)

        if async_mode:
            # Submit async job
            job = run_sync_with_retry(
                service.submit_job,
                query,
                service="vo_tap",
            )
            job.run()

            # Poll for completion
            import time

            max_wait = 300  # 5 minutes
            elapsed = 0
            while job.phase not in ("COMPLETED", "ERROR", "ABORTED"):
                time.sleep(2)
                elapsed += 2
                if elapsed > max_wait:
                    job.abort()
                    raise MCPError(
                        code=ErrorCode.TIMEOUT_ERROR,
                        message="Async TAP job timed out",
                        service="vo_tap",
                        recoverable=True,
                        suggestion="Try a smaller query or increase timeout",
                        details={"url": url, "elapsed": elapsed},
                    )

            if job.phase == "ERROR":
                raise MCPError(
                    code=ErrorCode.SERVICE_ERROR,
                    message=f"TAP job failed: {job.phase}",
                    service="vo_tap",
                    recoverable=False,
                    suggestion="Check the ADQL query syntax",
                    details={"url": url, "phase": job.phase},
                )

            result = job.fetch_result()
        else:
            # Sync query
            result = run_sync_with_retry(
                service.search,
                query,
                maxrec=max_rows,
                service="vo_tap",
            )

        if result is None:
            return {
                "success": True,
                "service": "vo_tap",
                "query": {"url": url, "adql": query},
                "total_count": 0,
                "returned_count": 0,
                "data": [],
            }

        # Convert to table then records
        table = result.to_table()
        records = table_to_records(table)

        return {
            "success": True,
            "service": "vo_tap",
            "query": {"url": url, "adql": query, "async": async_mode},
            "total_count": len(records),
            "returned_count": len(records),
            "data": records,
            "truncated": len(records) >= max_rows,
        }

    except MCPError:
        raise
    except Exception as e:
        raise MCPError(
            code=ErrorCode.SERVICE_ERROR,
            message=f"TAP query failed: {str(e)}",
            service="vo_tap",
            recoverable=True,
            suggestion="Check ADQL syntax and service availability",
            details={"url": url, "query": query, "error": str(e)},
        )


def tap_list_tables(service_url: str) -> dict[str, Any]:
    """List tables available at a TAP service.

    Args:
        service_url: TAP service URL or alias

    Returns:
        List of tables.
    """
    import pyvo

    url = _resolve_service_url(service_url, "tap")

    try:
        service = pyvo.dal.TAPService(url)

        tables = []
        for schema in service.tables:
            for table in service.tables[schema]:
                tables.append({
                    "schema": schema,
                    "name": table.name,
                    "description": table.description or "",
                })

        return {
            "success": True,
            "service": "vo_tap",
            "url": url,
            "table_count": len(tables),
            "tables": tables,
        }

    except Exception as e:
        raise MCPError(
            code=ErrorCode.SERVICE_ERROR,
            message=f"Failed to list tables: {str(e)}",
            service="vo_tap",
            recoverable=True,
            suggestion="Check service URL",
            details={"url": url, "error": str(e)},
        )


def tap_table_schema(service_url: str, table_name: str) -> dict[str, Any]:
    """Get schema for a TAP table.

    Args:
        service_url: TAP service URL or alias
        table_name: Table name

    Returns:
        Table schema with columns.
    """
    import pyvo

    url = _resolve_service_url(service_url, "tap")

    try:
        service = pyvo.dal.TAPService(url)

        # Find the table
        table = None
        for schema in service.tables:
            for t in service.tables[schema]:
                if t.name == table_name or t.name.endswith(f".{table_name}"):
                    table = t
                    break
            if table:
                break

        if table is None:
            raise MCPError(
                code=ErrorCode.NOT_FOUND,
                message=f"Table not found: {table_name}",
                service="vo_tap",
                recoverable=False,
                suggestion="Use tap_list_tables to see available tables",
                details={"url": url, "table": table_name},
            )

        columns = []
        for col in table.columns:
            columns.append({
                "name": col.name,
                "datatype": str(col.datatype) if col.datatype else None,
                "description": col.description or "",
                "unit": str(col.unit) if col.unit else None,
                "ucd": col.ucd or "",
            })

        return {
            "success": True,
            "service": "vo_tap",
            "url": url,
            "table": table_name,
            "description": table.description or "",
            "column_count": len(columns),
            "columns": columns,
        }

    except MCPError:
        raise
    except Exception as e:
        raise MCPError(
            code=ErrorCode.SERVICE_ERROR,
            message=f"Failed to get table schema: {str(e)}",
            service="vo_tap",
            recoverable=True,
            suggestion="Check table name",
            details={"url": url, "table": table_name, "error": str(e)},
        )


def sia_search(
    service_url: str,
    ra: float,
    dec: float,
    radius: float,
    format: str | None = None,
) -> dict[str, Any]:
    """Search for images using SIA.

    Args:
        service_url: SIA service URL
        ra: Right ascension in degrees
        dec: Declination in degrees
        radius: Search radius in degrees
        format: Image format filter

    Returns:
        Image access URLs.
    """
    import pyvo

    validate_coordinates(ra, dec)

    url = _resolve_service_url(service_url, "sia")

    try:
        service = pyvo.dal.SIAService(url)

        # Search for images
        result = run_sync_with_retry(
            service.search,
            pos=(ra, dec),
            size=radius,
            service="vo_sia",
        )

        if result is None or len(result) == 0:
            return {
                "success": True,
                "service": "vo_sia",
                "query": {"url": url, "ra": ra, "dec": dec, "radius": radius},
                "total_count": 0,
                "returned_count": 0,
                "data": [],
            }

        # Convert to records
        images = []
        for row in result:
            img = {
                "access_url": str(row.getdataurl()) if row.getdataurl() else None,
                "format": str(row.get("format", "")) if row.get("format") else None,
                "title": str(row.get("title", "")) if row.get("title") else None,
                "ra": float(row.get("ra", ra)),
                "dec": float(row.get("dec", dec)),
            }

            # Filter by format if specified
            if format and img["format"] and format.lower() not in img["format"].lower():
                continue

            images.append(img)

        return {
            "success": True,
            "service": "vo_sia",
            "query": {"url": url, "ra": ra, "dec": dec, "radius": radius, "format": format},
            "total_count": len(images),
            "returned_count": len(images),
            "data": images,
        }

    except MCPError:
        raise
    except Exception as e:
        raise MCPError(
            code=ErrorCode.SERVICE_ERROR,
            message=f"SIA search failed: {str(e)}",
            service="vo_sia",
            recoverable=True,
            suggestion="Check coordinates and service URL",
            details={"url": url, "ra": ra, "dec": dec, "error": str(e)},
        )


def ssa_search(
    service_url: str,
    ra: float,
    dec: float,
    radius: float,
    band: tuple | None = None,
) -> dict[str, Any]:
    """Search for spectra using SSA.

    Args:
        service_url: SSA service URL
        ra: Right ascension in degrees
        dec: Declination in degrees
        radius: Search radius in degrees
        band: Wavelength range (min, max) in meters

    Returns:
        Spectra access URLs.
    """
    import pyvo

    validate_coordinates(ra, dec)

    url = _resolve_service_url(service_url, "ssa")

    try:
        service = pyvo.dal.SSAService(url)

        # Build search params
        kwargs = {"pos": (ra, dec), "diameter": radius * 2}
        if band:
            kwargs["band"] = band

        result = run_sync_with_retry(
            service.search,
            service="vo_ssa",
            **kwargs,
        )

        if result is None or len(result) == 0:
            return {
                "success": True,
                "service": "vo_ssa",
                "query": {"url": url, "ra": ra, "dec": dec, "radius": radius},
                "total_count": 0,
                "returned_count": 0,
                "data": [],
            }

        # Convert to records
        spectra = []
        for row in result:
            spec = {
                "access_url": str(row.getdataurl()) if row.getdataurl() else None,
                "format": str(row.get("format", "")) if row.get("format") else None,
                "title": str(row.get("title", "")) if row.get("title") else None,
                "ra": float(row.get("ra", ra)),
                "dec": float(row.get("dec", dec)),
            }
            spectra.append(spec)

        return {
            "success": True,
            "service": "vo_ssa",
            "query": {"url": url, "ra": ra, "dec": dec, "radius": radius, "band": band},
            "total_count": len(spectra),
            "returned_count": len(spectra),
            "data": spectra,
        }

    except MCPError:
        raise
    except Exception as e:
        raise MCPError(
            code=ErrorCode.SERVICE_ERROR,
            message=f"SSA search failed: {str(e)}",
            service="vo_ssa",
            recoverable=True,
            suggestion="Check coordinates and service URL",
            details={"url": url, "ra": ra, "dec": dec, "error": str(e)},
        )


def discover_services(resource_type: str, keywords: str | None = None) -> dict[str, Any]:
    """Discover VO services.

    Args:
        resource_type: Service type ('tap', 'sia', 'ssa', 'cone')
        keywords: Search keywords

    Returns:
        List of VO resources.
    """
    import pyvo

    # Map resource types to VO registry types
    type_map = {
        "tap": "vs:CatalogService",
        "sia": "vs:CatalogService",
        "ssa": "vs:CatalogService",
        "cone": "vs:CatalogService",
    }

    try:
        # Search the registry
        if keywords:
            results = pyvo.regsearch(keywords=keywords)
        else:
            results = pyvo.regsearch(servicetype=resource_type)

        services = []
        for res in results:
            try:
                service = {
                    "ivoid": str(res.ivoid) if res.ivoid else "",
                    "short_name": str(res.short_name) if res.short_name else "",
                    "title": str(res.res_title) if res.res_title else "",
                    "description": str(res.res_description)[:500] if res.res_description else "",
                    "access_url": str(res.access_url) if res.access_url else "",
                    "service_type": resource_type,
                }
                if service["access_url"]:
                    services.append(service)
            except Exception:
                continue

        return {
            "success": True,
            "service": "vo_registry",
            "query": {"resource_type": resource_type, "keywords": keywords},
            "total_count": len(services),
            "returned_count": len(services),
            "data": services[:100],  # Limit results
        }

    except Exception as e:
        raise MCPError(
            code=ErrorCode.SERVICE_ERROR,
            message=f"VO registry search failed: {str(e)}",
            service="vo_registry",
            recoverable=True,
            suggestion="Try different keywords",
            details={"resource_type": resource_type, "keywords": keywords, "error": str(e)},
        )
