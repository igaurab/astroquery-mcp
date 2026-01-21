"""Authentication management for astroquery MCP server."""

import os
from typing import Any

from config import get_config
from models.errors import ErrorCode, MCPError


def get_token(service: str) -> str | None:
    """Get authentication token for a service.

    Args:
        service: Service name (e.g., 'ads', 'mast')

    Returns:
        Token string or None if not configured.
    """
    config = get_config()

    if service not in config.auth:
        return None

    token_env = config.auth[service].token_env
    return os.environ.get(token_env)


def require_token(service: str) -> str:
    """Get authentication token, raising error if not found.

    Args:
        service: Service name (e.g., 'ads', 'mast')

    Returns:
        Token string.

    Raises:
        MCPError: If token is not configured.
    """
    token = get_token(service)

    if not token:
        config = get_config()
        token_env = config.auth.get(service, {})
        env_var = (
            token_env.token_env
            if hasattr(token_env, "token_env")
            else f"{service.upper()}_TOKEN"
        )

        raise MCPError(
            code=ErrorCode.AUTHENTICATION_ERROR,
            message=f"Authentication required for {service}",
            service=service,
            recoverable=False,
            suggestion=f"Set the {env_var} environment variable with your API token",
            details={"env_var": env_var},
        )

    return token


def configure_astroquery_auth() -> dict[str, Any]:
    """Configure astroquery modules with available tokens.

    Returns:
        Dict of configured services and their status.
    """
    configured = {}

    # Configure ADS token
    ads_token = get_token("ads")
    if ads_token:
        try:
            from astroquery.nasa_ads import ADS

            ADS.TOKEN = ads_token
            configured["ads"] = True
        except ImportError:
            configured["ads"] = False

    # Configure MAST token (optional)
    mast_token = get_token("mast")
    if mast_token:
        try:
            from astroquery.mast import Observations

            Observations.login(token=mast_token)
            configured["mast"] = True
        except (ImportError, Exception):
            configured["mast"] = False

    return configured


def check_auth_status() -> dict[str, dict[str, Any]]:
    """Check authentication status for all services.

    Returns:
        Dict with service names as keys and status info as values.
    """
    config = get_config()
    status = {}

    for service, auth_config in config.auth.items():
        token = os.environ.get(auth_config.token_env)
        status[service] = {
            "configured": token is not None,
            "env_var": auth_config.token_env,
            "required": service == "ads",  # Only ADS is strictly required
        }

    return status
