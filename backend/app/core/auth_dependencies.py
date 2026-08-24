"""
FastAPI dependencies that gate access to protected routes.

Two dependencies are defined here: ``require_authenticated_user`` (any
enrolled, logged-in person) and ``require_admin`` (enrolled, logged-in, and
role ``"admin"``). Both are plain callables usable with FastAPI's
``Depends()``, which also makes them directly overridable in tests via
``app.dependency_overrides``.

The session cookie set during login stores only an opaque ``user_id`` -- it
never stores a role or an ``is_admin`` flag. Every request re-fetches the
role fresh from the database through ``get_user_by_id()``. This is
deliberate: a client-supplied authorization flag is exactly the mistake to
avoid, since it can be forged. Re-deriving role from the database on every
request means nothing the browser sends is ever trusted for that decision.

How this file connects to the project
--------------------------------------
- ``db/user_repository.py`` supplies ``get_user_by_id()``.
- ``db/database.py`` supplies ``get_db_session()``.
- ``app/api/validate.py``, ``generate.py``, ``projects.py`` use
  ``require_authenticated_user`` at router level.
- ``app/api/database_management.py`` and ``app/api/users.py`` use
  ``require_admin`` at router level.
- ``app/api/identifier_database.py`` uses both, one per route, since that
  file mixes an admin-only route with a member-accessible one.
- ``app/api/auth.py`` uses ``require_authenticated_user`` for ``/auth/me``
  and ``/auth/logout``.
- ``app/main.py`` uses the same session lookup logic (via a shared helper)
  to gate page requests, not just API requests.
"""

import os

from fastapi import Depends, HTTPException, Request
from sqlalchemy.orm import Session

from db.database import get_db_session
from db.models import User
from db.user_repository import get_user_by_id


_DEV_BYPASS_USER = User(
    id=0,
    email="dev@local",
    name="Local dev (AUTH_REQUIRED=false)",
    role="admin",
)


def _auth_required() -> bool:
    """
    Read whether the login gate is active.

    Defaults to required (fails safe). Only an explicit ``AUTH_REQUIRED=false``
    disables the gate, intended for local ``npm run dev`` frontend iteration
    where CILogon's registered redirect URI does not apply anyway. Production
    must never set this to anything but ``true`` or leave it unset.
    """
    return (
        os.getenv("AUTH_REQUIRED", "true").strip().lower()
        != "false"
    )


def require_authenticated_user(
    request: Request,
    session: Session = Depends(get_db_session),
) -> User:
    """
    Require a valid, still-enrolled session.

    Raises
    ------
    HTTPException
        401 when there is no session, or when the session refers to a user
        who no longer exists (for example, an admin removed their
        enrollment after they logged in).
    """
    if not _auth_required():
        return _DEV_BYPASS_USER

    user_id = request.session.get("user_id")

    if user_id is None:
        raise HTTPException(
            status_code=401,
            detail="Authentication required.",
        )

    user = get_user_by_id(
        session,
        user_id=user_id,
    )

    if user is None:
        request.session.clear()

        raise HTTPException(
            status_code=401,
            detail="Session is no longer valid.",
        )

    return user


def require_admin(
    user: User = Depends(require_authenticated_user),
) -> User:
    """
    Require a valid session belonging to an admin.

    Raises
    ------
    HTTPException
        403 when the authenticated user's role is not ``"admin"``.
    """
    if user.role != "admin":
        raise HTTPException(
            status_code=403,
            detail="Administrator access is required.",
        )

    return user
