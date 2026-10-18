"""The rules about the key the API requires.

They live here rather than beside the routes, because the command that starts
the server needs them too, and the menu has to keep working without the api
extra installed.
"""

import os
import secrets
from typing import Optional

API_KEY_VARIABLE = "DUEWRIGHT_API_KEY"
HEADER_NAME = "X-API-Key"
MINIMUM_KEY_LENGTH = 16

GENERATE_A_KEY = 'python -c "import secrets; print(secrets.token_urlsafe(32))"'


def expected_key() -> str:
    """Return the key the server expects, or an empty string when none is set."""
    return os.environ.get(API_KEY_VARIABLE, "")


def key_problem() -> Optional[str]:
    """Return why the configured key cannot be used, or None when it can.

    The server refuses to start on a problem, and every request fails closed as
    well, so a misconfiguration is never a quiet one.
    """
    key = expected_key()
    if not key:
        return f"{API_KEY_VARIABLE} is not set"
    if len(key) < MINIMUM_KEY_LENGTH:
        return f"{API_KEY_VARIABLE} is shorter than {MINIMUM_KEY_LENGTH} characters"
    return None


def keys_match(provided: str) -> bool:
    """Return True when the provided key is the one the server expects.

    The comparison takes the same time whatever the two keys are, so it cannot
    be used to guess the key a character at a time. Encoding to bytes keeps a
    key with characters outside ASCII from raising.
    """
    expected = expected_key()
    if not expected or not provided:
        return False
    return secrets.compare_digest(provided.encode(), expected.encode())
