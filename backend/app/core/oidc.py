"""
CILogon / OIDC login integration.

This module builds the Authlib OIDC client and implements the two moving
parts of the login flow: sending someone to CILogon, and handling the
identity CILogon hands back afterward.

Logging in through CILogon only proves who someone is. Access itself is
decided by COManage group membership, released as the ``groups`` claim on
the ID token and matched in ``core/comanage_groups.py`` -- not by anything
in the app's own database. ``process_callback()`` is where that admission
check happens: no recognized role in ``groups`` means no access, full stop,
even for someone who already has a row in ``db/user_repository.py`` from
before this model.

The ``users`` table still exists, but only as a local, queryable mirror of
who currently has access (what the read-only User Management page shows)
-- kept in sync on every login, not consulted to grant access on its own.
``scripts/seed_admin.py`` predates this model and is no longer how anyone
gets in.

How this file connects to the project
--------------------------------------
- ``app/main.py`` calls ``redirect_to_cilogon()`` when an unauthenticated
  visitor is not mid-callback, and ``process_callback()`` when a request to
  the root path carries ``code``/``state`` query parameters.
- ``core/comanage_groups.py`` decides the role from the ``groups`` claim.
- ``db/user_repository.py`` supplies the mirror-table reads/writes used
  here.
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

import base64
import json
import logging
import os

from authlib.integrations.starlette_client import OAuth
from fastapi import Request
from sqlalchemy.orm import Session
from starlette.responses import RedirectResponse

from core.comanage_groups import resolve_role_from_groups
from db.user_repository import (
    bind_cilogon_sub,
    create_user,
    get_user_by_email,
    get_user_by_sub,
    sync_role_from_comanage,
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


logger = logging.getLogger(__name__)

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
    issuer, audience -- handled by Authlib), and decides access purely from
    the ID token's ``groups`` claim (see ``core/comanage_groups.py``): no
    recognized role for this app's COU means no access, regardless of any
    pre-existing row in the app's own ``users`` table. When a role is
    resolved, that table is upserted to mirror it -- creating the row on
    someone's first login, or correcting its ``role`` if COManage's answer
    has changed since their last one (e.g. an admin demoted to member, or
    vice versa).

    Returns
    -------
    User
        The user record, kept in sync with the role COManage just
        reported -- newly created on a first login, or updated in place.

    Raises
    ------
    UnenrolledUserError
        Raised when the ``groups`` claim carries no recognized role for
        this app's COU.
    """
    client = get_oauth_client()
    token = await client.authorize_access_token(request)

    claims = token.get("userinfo") or {}

    # TEMPORARY -- checking whether the groups claim now shows up after
    # Paul enabled attribute release. Remove once confirmed; do not ship
    # this logging permanently -- it prints full identity claims.
    logger.warning("TEMP DEBUG -- ID token claims: %s", claims)

    # TEMPORARY -- manually decode the raw JWT payload ourselves (just
    # base64 + stdlib json, no Authlib involved) to rule out Authlib
    # filtering/stripping a claim during its own parsing. This is the raw
    # bytes CILogon sent, completely independent of our session/cookie
    # handling and of Authlib's userinfo parsing.
    id_token_raw = token.get("id_token")
    if id_token_raw:
        try:
            payload_segment = id_token_raw.split(".")[1]
            padded = payload_segment + "=" * (-len(payload_segment) % 4)
            raw_payload = json.loads(base64.urlsafe_b64decode(padded))
            logger.warning(
                "TEMP DEBUG -- raw JWT payload, manually decoded (no Authlib): %s",
                raw_payload,
            )
        except Exception:
            logger.exception(
                "TEMP DEBUG -- manual JWT decode failed"
            )

    try:
        userinfo_response = await client.userinfo(token=token)
        logger.warning(
            "TEMP DEBUG -- /userinfo endpoint response: %s",
            userinfo_response,
        )
    except Exception:
        logger.exception(
            "TEMP DEBUG -- calling the /userinfo endpoint failed"
        )

    cilogon_sub = claims.get("sub")
    email = claims.get("email")
    name = claims.get("name")

    if not cilogon_sub or not email:
        raise RuntimeError(
            "CILogon response did not include the expected "
            "'sub' and 'email' claims."
        )

    # COManage group membership is the sole admission decision. The
    # app's own `users` table no longer grants access on its own -- it is
    # kept in sync here purely as a local, queryable mirror of who
    # currently has access (what the read-only User Management page
    # displays), not as a second, independent enrollment path.
    role = resolve_role_from_groups(claims.get("groups"))

    if role is None:
        raise UnenrolledUserError(email)

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
        user = create_user(
            session,
            email=email,
            role=role,
            name=name,
            cilogon_sub=cilogon_sub,
        )
        logger.info(
            "Auto-enrolled '%s' as %s via COManage group membership.",
            email,
            role,
        )
    else:
        user = sync_role_from_comanage(
            session,
            user_id=user.id,
            role=role,
        )

    touch_last_login(
        session,
        user_id=user.id,
    )

    if name and not user.name:
        user.name = name
        session.commit()
        session.refresh(user)

    return user
