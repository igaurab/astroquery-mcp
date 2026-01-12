"""ADS literature search tools."""

from typing import Any

from auth import require_token
from config import get_config
from models.errors import MCPError, ErrorCode
from retry import run_sync_with_retry


# Default fields to retrieve
DEFAULT_FIELDS = [
    "bibcode",
    "title",
    "author",
    "abstract",
    "pubdate",
    "pub",
    "doi",
    "citation_count",
    "keyword",
    "identifier",
]


def _configure_ads():
    """Configure ADS with token."""
    from astroquery.nasa_ads import ADS

    token = require_token("ads")
    ADS.TOKEN = token
    return ADS


def search_papers(
    query: str,
    page: int = 1,
    rows_per_page: int = 100,
    sort: str = "date desc",
    fields: list[str] | None = None,
) -> dict[str, Any]:
    """Search ADS for papers.

    Args:
        query: ADS search query
        page: Page number (1-indexed)
        rows_per_page: Results per page (max 1000)
        sort: Sort order
        fields: Fields to return

    Returns:
        Search results with papers.
    """
    ADS = _configure_ads()
    config = get_config()

    # Validate parameters
    rows_per_page = min(rows_per_page, 1000)
    page = max(1, page)

    # Calculate start position
    start = (page - 1) * rows_per_page

    # Use default fields if not specified
    if fields is None:
        fields = DEFAULT_FIELDS

    try:
        # Configure query
        ADS.NROWS = rows_per_page
        ADS.START = start
        ADS.SORT = sort
        ADS.ADS_FIELDS = fields

        # Execute search with retry
        result = run_sync_with_retry(
            ADS.query_simple,
            query,
            service="ads",
        )

        if result is None or len(result) == 0:
            return {
                "success": True,
                "service": "ads",
                "query": {"query": query, "page": page, "rows_per_page": rows_per_page},
                "total_count": 0,
                "returned_count": 0,
                "data": [],
            }

        # Convert to paper records
        papers = []
        for row in result:
            paper = {
                "bibcode": str(row.get("bibcode", "")),
                "title": str(row.get("title", [""])[0]) if row.get("title") else "",
                "authors": list(row.get("author", [])) if row.get("author") else [],
                "abstract": str(row.get("abstract", "")) if row.get("abstract") else None,
                "pub_date": str(row.get("pubdate", "")) if row.get("pubdate") else None,
                "journal": str(row.get("pub", "")) if row.get("pub") else None,
                "doi": str(row.get("doi", [""])[0]) if row.get("doi") else None,
                "citation_count": int(row.get("citation_count", 0)) if row.get("citation_count") else 0,
                "keywords": list(row.get("keyword", [])) if row.get("keyword") else [],
            }
            papers.append(paper)

        return {
            "success": True,
            "service": "ads",
            "query": {"query": query, "page": page, "rows_per_page": rows_per_page, "sort": sort},
            "total_count": len(result),  # Note: ADS doesn't always return total
            "returned_count": len(papers),
            "data": papers,
            "truncated": len(papers) == rows_per_page,
        }

    except MCPError:
        raise
    except Exception as e:
        raise MCPError(
            code=ErrorCode.SERVICE_ERROR,
            message=f"ADS search failed: {str(e)}",
            service="ads",
            recoverable=True,
            suggestion="Check query syntax or try again later",
            details={"query": query, "error": str(e)},
        )


def get_record(bibcode: str, fields: list[str] | None = None) -> dict[str, Any]:
    """Get a single paper by bibcode.

    Args:
        bibcode: ADS bibcode
        fields: Fields to return

    Returns:
        Paper metadata.
    """
    ADS = _configure_ads()

    if fields is None:
        fields = DEFAULT_FIELDS

    try:
        ADS.ADS_FIELDS = fields

        result = run_sync_with_retry(
            ADS.query_simple,
            f"bibcode:{bibcode}",
            service="ads",
        )

        if result is None or len(result) == 0:
            raise MCPError(
                code=ErrorCode.BIBCODE_NOT_FOUND,
                message=f"Bibcode not found: {bibcode}",
                service="ads",
                recoverable=False,
                suggestion="Check the bibcode format",
                details={"bibcode": bibcode},
            )

        row = result[0]

        return {
            "bibcode": str(row.get("bibcode", bibcode)),
            "title": str(row.get("title", [""])[0]) if row.get("title") else "",
            "authors": list(row.get("author", [])) if row.get("author") else [],
            "abstract": str(row.get("abstract", "")) if row.get("abstract") else None,
            "pub_date": str(row.get("pubdate", "")) if row.get("pubdate") else None,
            "journal": str(row.get("pub", "")) if row.get("pub") else None,
            "doi": str(row.get("doi", [""])[0]) if row.get("doi") else None,
            "citation_count": int(row.get("citation_count", 0)) if row.get("citation_count") else 0,
            "keywords": list(row.get("keyword", [])) if row.get("keyword") else [],
            "identifiers": list(row.get("identifier", [])) if row.get("identifier") else [],
        }

    except MCPError:
        raise
    except Exception as e:
        raise MCPError(
            code=ErrorCode.SERVICE_ERROR,
            message=f"ADS query failed: {str(e)}",
            service="ads",
            recoverable=True,
            suggestion="Try again later",
            details={"bibcode": bibcode, "error": str(e)},
        )


def get_links(bibcode: str, link_type: str | None = None) -> dict[str, Any]:
    """Get available links for a paper.

    Args:
        bibcode: ADS bibcode
        link_type: Specific link type to filter

    Returns:
        Dictionary of link types to URLs.
    """
    ADS = _configure_ads()

    try:
        # Query for link data
        ADS.ADS_FIELDS = ["bibcode", "links_data"]

        result = run_sync_with_retry(
            ADS.query_simple,
            f"bibcode:{bibcode}",
            service="ads",
        )

        if result is None or len(result) == 0:
            raise MCPError(
                code=ErrorCode.BIBCODE_NOT_FOUND,
                message=f"Bibcode not found: {bibcode}",
                service="ads",
                recoverable=False,
                suggestion="Check the bibcode format",
                details={"bibcode": bibcode},
            )

        # Build links dictionary
        links = {
            "abstract": f"https://ui.adsabs.harvard.edu/abs/{bibcode}/abstract",
            "citations": f"https://ui.adsabs.harvard.edu/abs/{bibcode}/citations",
            "references": f"https://ui.adsabs.harvard.edu/abs/{bibcode}/references",
        }

        # Add PDF links (common patterns)
        links["ads_pdf"] = f"https://ui.adsabs.harvard.edu/link_gateway/{bibcode}/EPRINT_PDF"
        links["arxiv"] = f"https://arxiv.org/abs/{bibcode}" if "arXiv" in bibcode else None

        # Filter by link type if specified
        if link_type:
            links = {k: v for k, v in links.items() if k == link_type and v is not None}

        return {
            "bibcode": bibcode,
            "links": {k: v for k, v in links.items() if v is not None},
        }

    except MCPError:
        raise
    except Exception as e:
        raise MCPError(
            code=ErrorCode.SERVICE_ERROR,
            message=f"Failed to get links: {str(e)}",
            service="ads",
            recoverable=True,
            suggestion="Try again later",
            details={"bibcode": bibcode, "error": str(e)},
        )


def get_fulltext(bibcode: str, prefer_format: str = "pdf") -> dict[str, Any]:
    """Get full text URL for a paper.

    Args:
        bibcode: ADS bibcode
        prefer_format: Preferred format ('pdf' or 'html')

    Returns:
        URL to full text or content info.
    """
    # Get available links
    links_result = get_links(bibcode)
    links = links_result.get("links", {})

    result = {
        "bibcode": bibcode,
        "format": prefer_format,
    }

    # Try to find the preferred format
    if prefer_format == "pdf":
        if "ads_pdf" in links:
            result["url"] = links["ads_pdf"]
            result["source"] = "ads"
        elif "arxiv" in links:
            # Convert arXiv abstract to PDF
            arxiv_url = links["arxiv"]
            result["url"] = arxiv_url.replace("/abs/", "/pdf/") + ".pdf"
            result["source"] = "arxiv"
    else:
        if "abstract" in links:
            result["url"] = links["abstract"]
            result["source"] = "ads"

    if "url" not in result:
        result["error"] = "Full text not available"
        result["available_links"] = links

    return result
