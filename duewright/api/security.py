"""The API's way of asking for the key.

The rules themselves live in duewright/security.py, because the command that
starts the server applies them before the server is up.
"""

from typing import Annotated, Optional

from fastapi import Depends, HTTPException, status
from fastapi.security import APIKeyHeader

from duewright.security import HEADER_NAME, keys_match

# auto_error=False, so a missing header is answered by this module with the
# same 401 as a wrong one rather than by FastAPI with its own message.
api_key_header = APIKeyHeader(name=HEADER_NAME, auto_error=False)


def require_api_key(provided: Annotated[Optional[str], Depends(api_key_header)]) -> None:
    """Refuse the request unless it carries the key the server expects."""
    if not provided or not keys_match(provided):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or missing API key",
        )
