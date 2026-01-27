"""Custom ADS query tools optimized for context efficiency.

This module provides specialized ADS query functions that return only
essential fields by default, reducing token usage significantly.
"""

import logging
from typing import Any, Literal

from astropy.table import Table
from models.errors import MCPError, ErrorCode

logger = logging.getLogger(__name__)

# Field presets for different use cases
FIELD_PRESETS = {
    "minimal": [
        "bibcode",
        "title",
        "first_author",
        "year",
        "citation_count",
    ],
    "standard": [
        "bibcode",
        "title",
        "first_author",
        "author",  # Full author list
        "year",
        "pubdate",
        "citation_count",
        "doi",
        "pub",  # Journal/publication
        "abstract",
    ],
    "extended": [
        "bibcode",
        "title",
        "first_author",
        "author",
        "year",
        "pubdate",
        "citation_count",
        "doi",
        "pub",
        "volume",
        "page",
        "keyword",
        "abstract",  # Include abstract for extended
    ],
    "full": None,  # Return all fields (default astroquery behavior)
}


def filter_ads_result(
    result: Table,
    fields: list[str] | None = None,
    max_results: int | None = None,
    truncate_abstract: int = 200,
    max_authors: int | None = None,
) -> dict[str, Any]:
    """Filter and optimize ADS query results for context efficiency.

    Args:
        result: Astropy Table from ADS query
        fields: List of field names to include. If None, includes all fields.
        max_results: Maximum number of results to return
        truncate_abstract: Truncate abstracts to this many characters (0 = no truncate)
        max_authors: Maximum number of authors to include per paper

    Returns:
        Dict with filtered results and metadata
    """
    if result is None or len(result) == 0:
        return {
            "count": 0,
            "results": [],
            "message": "No results found",
        }

    # Limit number of results
    if max_results and len(result) > max_results:
        result = result[:max_results]
        truncated = True
    else:
        truncated = False

    # Get column names
    available_fields = result.colnames

    # Filter to requested fields
    if fields:
        # Only keep fields that exist in the result
        fields_to_keep = [f for f in fields if f in available_fields]
        if not fields_to_keep:
            logger.warning(f"None of requested fields {fields} found in result")
            fields_to_keep = available_fields
    else:
        fields_to_keep = available_fields

    # Convert to list of dicts with optimizations
    results_list = []
    for row in result:
        paper = {}
        for field in fields_to_keep:
            value = row[field]

            # Handle abstracts - truncate if requested
            if field == "abstract" and truncate_abstract > 0 and value:
                if isinstance(value, list):
                    value = value[0] if value else ""
                if isinstance(value, str) and len(value) > truncate_abstract:
                    value = value[:truncate_abstract] + "..."

            # Handle authors - limit if requested
            elif field == "author" and max_authors and value:
                if isinstance(value, list) and len(value) > max_authors:
                    value = value[:max_authors] + [f"... and {len(value) - max_authors} more"]

            # Handle other list fields
            elif isinstance(value, list):
                # Keep lists as-is but convert numpy types
                value = [str(v) if hasattr(v, "item") else v for v in value]

            # Handle masked values (missing data)
            elif hasattr(value, "mask") and value.mask:
                value = None

            # Handle numpy scalar types (check for size == 1 to avoid array error)
            elif hasattr(value, "item") and (not hasattr(value, "size") or value.size == 1):
                value = value.item()

            # Handle numpy arrays that aren't scalars - convert to list
            elif hasattr(value, "tolist"):
                value = value.tolist()

            paper[field] = value

        results_list.append(paper)

    return {
        "count": len(results_list),
        "total_found": len(result) if not truncated else f"{len(result)}+",
        "truncated": truncated,
        "results": results_list,
        "fields": fields_to_keep,
    }


def query_ads_compact(
    query_string: str,
    fields: Literal["minimal", "standard", "extended", "full"] | list[str] = "standard",
    max_results: int = 10,
    sort: str = "citation_count desc",
    rows: int = 50,
) -> dict[str, Any]:
    """Query ADS with compact, context-efficient results.

    This is a specialized version of ADS.query_simple that returns only
    essential fields by default, dramatically reducing token usage.

    Args:
        query_string: ADS query string (e.g., "black hole X-ray")
        fields: Field preset name or custom list of fields:
            - "minimal": bibcode, title, first_author, year, citations (5 fields)
            - "standard": + author list, date, DOI, journal, abstract (10 fields)
            - "extended": + volume, page, keywords (13 fields)
            - "full": All fields (may use lots of tokens)
            - Custom list: ["bibcode", "title", "year", ...]
        max_results: Maximum results to return (default: 10)
        sort: Sort order (default: "citation_count desc" for most cited first)
        rows: How many rows to fetch from ADS (default: 50, then filtered)

    Returns:
        Dict with count, results (list of papers), and metadata

    Example:
        >>> query_ads_compact("NGC 3783", fields="minimal", max_results=5)
        {
            "count": 5,
            "total_found": 50,
            "truncated": True,
            "results": [
                {
                    "bibcode": "2023ApJ...",
                    "title": ["NGC 3783: X-ray variability..."],
                    "first_author": "Smith, J.",
                    "year": "2023",
                    "citation_count": 15
                },
                ...
            ],
            "fields": ["bibcode", "title", "first_author", "year", "citation_count"]
        }
    """
    try:
        from astroquery.nasa_ads import ADS

        # Determine which fields to request
        if isinstance(fields, str):
            if fields not in FIELD_PRESETS:
                raise MCPError(
                    code=ErrorCode.VALIDATION_ERROR,
                    message=f"Invalid field preset: {fields}",
                    service="ads_compact",
                    recoverable=True,
                    suggestion=f"Use one of: {', '.join(FIELD_PRESETS.keys())}",
                )
            field_list = FIELD_PRESETS[fields]
        else:
            field_list = fields

        # Configure ADS query
        logger.info(f"Querying ADS: '{query_string}' (rows={rows}, sort={sort})")

        # Perform query with field selection if not "full"
        if field_list is not None:
            # Use ADS with fl (field list) parameter
            result = ADS.query_simple(
                query_string,
            )
            # ADS.query_simple doesn't support fl parameter directly
            # We'll filter after querying
        else:
            # Full query
            result = ADS.query_simple(query_string)

        # Filter and optimize results
        filtered = filter_ads_result(
            result,
            fields=field_list,
            max_results=max_results,
            truncate_abstract=200,
            max_authors=10,
        )

        return {
            "success": True,
            "query": query_string,
            "preset": fields if isinstance(fields, str) else "custom",
            **filtered,
        }

    except ImportError as e:
        raise MCPError(
            code=ErrorCode.SERVICE_ERROR,
            message=f"ADS module not available: {e}",
            service="ads_compact",
            recoverable=False,
            suggestion="Install astroquery with ADS support",
        )
    except Exception as e:
        raise MCPError(
            code=ErrorCode.SERVICE_ERROR,
            message=f"ADS query failed: {e}",
            service="ads_compact",
            recoverable=True,
            suggestion="Check query syntax and try again",
            details={"query": query_string, "error": str(e)},
        )


def get_paper_details(
    bibcode: str,
    fields: list[str] | None = None,
) -> dict[str, Any]:
    """Get detailed information about a specific paper by bibcode.

    Args:
        bibcode: ADS bibcode (e.g., "2023ApJ...123..456S")
        fields: Fields to return. If None, returns all fields.

    Returns:
        Dict with paper details
    """
    try:
        from astroquery.nasa_ads import ADS

        # Query by bibcode
        result = ADS.query_simple(f"bibcode:{bibcode}")

        if result is None or len(result) == 0:
            return {
                "success": False,
                "error": f"Paper not found: {bibcode}",
            }

        # Get first (should be only) result
        filtered = filter_ads_result(
            result,
            fields=fields,
            max_results=1,
            truncate_abstract=0,  # Don't truncate for single paper
            max_authors=None,  # Include all authors
        )

        return {
            "success": True,
            "bibcode": bibcode,
            **filtered,
        }

    except Exception as e:
        raise MCPError(
            code=ErrorCode.SERVICE_ERROR,
            message=f"Failed to get paper details: {e}",
            service="ads_details",
            recoverable=True,
            suggestion="Check bibcode format",
            details={"bibcode": bibcode, "error": str(e)},
        )
