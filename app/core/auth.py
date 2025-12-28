"""API key authentication."""

import logging
from typing import Annotated

from fastapi import Depends, HTTPException, status
from fastapi.security import APIKeyHeader

from app.config import get_settings

logger = logging.getLogger(__name__)

# API key header scheme
api_key_header = APIKeyHeader(
    name="X-API-Key",
    description="API key for authentication",
    auto_error=True,
)

async def verify_api_key(
    api_key: Annotated[str, Depends(api_key_header)],
) -> str:
    """Verify the API key from request header.

    Args:
        api_key: The API key from the X-API-Key header.

    Returns:
        The validated API key.

    Raises:
        HTTPException: If the API key is invalid.
    """
    settings = get_settings()

    if api_key != settings.api_key:
        logger.warning("Invalid API key attempt")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid API key",
            headers={"WWW-Authenticate": "ApiKey"},
        )

    return api_key
