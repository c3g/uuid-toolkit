"""
CILogon / OIDC login integration.

This module builds the Authlib OIDC client and implements the two moving
parts of the login flow: sending someone to CILogon, and handling the
identity CILogon hands back afterward.

Logging in through CILogon only proves who someone is. It does not by
itself grant access to the application -- a matching row must already exist
in ``db/user_repository.py`` (created by an admin, or by ``scripts/seed_admin.py``
for the very first admin). ``process_callback()`` is where that admission
check happens.

How this file connects to the project
--------------------------------------
- ``app/main.py`` calls ``redirect_to_cilogon()`` when an unauthenticated
  visitor is not mid-callback, and ``process_callback()`` when a request to
  the root path carries ``code``/``state`` query parameters.
- ``db/user_repository.py`` supplies the enrollment lookups used here.
- Requires Starlette's ``SessionMiddleware`` to already be installed on the
  app, since Authlib stores the OIDC ``state``/nonce in ``request.session``
  during the redirect and reads it back during the callback.

Environment variables
----------------------
``OIDC_ISSUER``, ``OIDC_CLIENT_ID``, ``OIDC_CLIENT_SECRET``, and
``OIDC_REDIRECT_URI`` are read lazily, inside ``get_oauth_client()``, rather
than at import time. Tests and CI import ``main.py`` without any of these
set, and an import-time check would break that.
"""

import os

from authlib.integrations.starlette_client import OAuth
from fastapi import Request
from sqlalchemy.orm import Session
from starlette.responses import RedirectResponse

from db.user_repository import (
    bind_cilogon_sub,
    get_user_by_email,
    get_user_by_sub,
    touch_last_login,
)
from db.models import User


class UnenrolledUserError(Exception):
    """
    Raised when a person authenticates successfully through CILogon but has
    not been enrolled by an admin.

    The email that authenticated is carried on the exception so the calling
    route can show it in the rejection message.
    """

    def __init__(self, email: str | None) -> None:
        self.email = email
        super().__init__(
            f"'{email}' authenticated but is not enrolled."
        )


_oauth_client = None


def get_oauth_client():
    """
    Build (once) and return the registered Authlib OIDC client for CILogon.

    Reads ``OIDC_ISSUER``, ``OIDC_CLIENT_ID``, ``OIDC_CLIENT_SECRET``, and
    ``OIDC_REDIRECT_URI`` from the environment the first time this is
    called, and caches the result for later calls.

    Raises
    ------
    RuntimeError
        Raised when one or more required OIDC environment variables are
        missing.
    """
    global _oauth_client

    if _oauth_client is not None:
        return _oauth_client

    issuer = os.getenv("OIDC_ISSUER")
    client_id = os.getenv("OIDC_CLIENT_ID")
    client_secret = os.getenv("OIDC_CLIENT_SECRET")
    redirect_uri = os.getenv("OIDC_REDIRECT_URI")

    missing_names = [
        name
        for name, value in (
            ("OIDC_ISSUER", issuer),
            ("OIDC_CLIENT_ID", client_id),
            ("OIDC_CLIENT_SECRET", client_secret),
            ("OIDC_REDIRECT_URI", redirect_uri),
        )
        if not value
    ]

    if missing_names:
        raise RuntimeError(
            "Missing required OIDC environment variables: "
            + ", ".join(missing_names)
        )

    registry = OAuth()

    registry.register(
        name="cilogon",
        client_id=client_id,
        client_secret=client_secret,
        server_metadata_url=(
            f"{issuer.rstrip('/')}/.well-known/openid-configuration"
        ),
        client_kwargs={
            "scope": "openid email profile org.cilogon.userinfo"
        },
    )

    _oauth_client = registry.cilogon

    return _oauth_client


async def redirect_to_cilogon(
    request: Request,
) -> RedirectResponse:
    """
    Send an unauthenticated visitor to the CILogon login page.

    The redirect target is the registered ``OIDC_REDIRECT_URI`` (the app's
    own root), not derived from the incoming request, since CILogon only
    accepts the exact URI it was registered with.
    """
    client = get_oauth_client()
    redirect_uri = os.getenv("OIDC_REDIRECT_URI")

    return await client.authorize_redirect(
        request,
        redirect_uri=redirect_uri,
    )


async def process_callback(
    request: Request,
    session: Session,
) -> User:
    """
    Handle the redirect CILogon sends back after a login attempt.

    Exchanges the authorization code, validates the ID token (signature,
    issuer, audience -- handled by Authlib), and looks up the authenticated
    identity in the app's own enrolled-users table.

    Returns
    -------
    User
        The enrolled user record, with ``cilogon_sub`` bound if this was
        their first successful login.

    Raises
    ------
    UnenrolledUserError
        Raised when the authenticated identity has no matching enrolled
        user, by ``sub`` or by ``email``.
    """
    client = get_oauth_client()
    token = await client.authorize_access_token(request)

    claims = token.get("userinfo") or {}

    cilogon_sub = claims.get("sub")
    email = claims.get("email")
    name = claims.get("name")

    if not cilogon_sub or not email:
        raise RuntimeError(
            "CILogon response did not include the expected "
            "'sub' and 'email' claims."
        )

    user = get_user_by_sub(
        session,
        cilogon_sub=cilogon_sub,
    )

    if user is None:
        candidate = get_user_by_email(
            session,
            email=email,
        )

        if candidate is not None and candidate.cilogon_sub is None:
            user = bind_cilogon_sub(
                session,
                user_id=candidate.id,
                cilogon_sub=cilogon_sub,
            )

    if user is None:
        raise UnenrolledUserError(email)

    touch_last_login(
        session,
        user_id=user.id,
    )

    if name and not user.name:
        user.name = name
        session.commit()
        session.refresh(user)

    return user
