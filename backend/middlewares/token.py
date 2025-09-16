from fastapi import HTTPException, Security
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from conf import settings

# HTTP Bearer authentication scheme
bearer_scheme = HTTPBearer()


def token_validator(
    credentials: HTTPAuthorizationCredentials = Security(bearer_scheme),
) -> bool:
    """
    Validate the bearer token provided in the `Authorization` header.

    Args:
        credentials: Extracted HTTP bearer credentials.

    Returns:
        True if the token matches the expected value.

    Raises:
        HTTPException: Raises 401 if the token is missing or invalid.
    """
    token = credentials.credentials
    # If the provided token does not match our configured token, reject
    if token != settings.AUTHORIZATION_TOKEN:
        raise HTTPException(
            status_code=401,
            detail="Unauthorized: Invalid token",
        )

    return True
