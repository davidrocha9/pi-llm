"""API key authentication."""

import hashlib
import hmac
import logging
from pathlib import Path
from typing import Annotated

from fastapi import Depends, HTTPException, status
from fastapi.security import APIKeyHeader

from app.config import get_settings
from app.core.keys import KeyStore

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
    # If a SQLite DB is configured, prefer DB-backed verification for
    # performance and centralized storage.
    db_path = settings.api_keys_db
    if db_path:
        # resolve relative path against repo root
        repo_root = Path(__file__).resolve().parents[2]
        p = Path(db_path)
        if not p.is_absolute():
            p = (repo_root / p).resolve()
        
        logger.info(f"Verifying API key using database at: {p}")
        try:
            ks = KeyStore(p)
            ok = ks.verify(api_key)
            ks.close()
            if ok:
                return api_key
        except Exception:
            # Fall back to previous file/env-based behaviour on error
            logger.exception(f"KeyStore error using {p} — falling back to file-based checks")

    # Reject absurdly long keys early to mitigate DoS via large headers
    if len(api_key) > 256:
        logger.warning("API key too long")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid API key",
        )

    # Hash the incoming key to compare with stored hashes. If a server-side
    # pepper is configured, use HMAC-SHA256 with the pepper as the key. This
    # prevents an attacker who obtains the stored hashes from verifying keys
    # offline without access to the server secret.
    if settings.api_key_pepper:
        hashed_input = hmac.new(
            settings.api_key_pepper.encode(), api_key.encode(), hashlib.sha256
        ).hexdigest()
    else:
        hashed_input = hashlib.sha256(api_key.encode()).hexdigest()

    # Use constant-time comparison to avoid timing attacks
    for stored in settings.valid_api_key_hashes:
        if hmac.compare_digest(hashed_input, stored):
            return api_key

    logger.warning("Invalid API key attempt")
    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid API key",
        headers={"WWW-Authenticate": "ApiKey"},
    )
