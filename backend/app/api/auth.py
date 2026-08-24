"""
API routes for the current login session.

This router exposes what the frontend needs to know about who is signed in,
and how to sign out. The actual login (redirect to CILogon) and callback
handling live in ``app/main.py`` instead of here, because CILogon's
registered redirect URI is the app's root path (``/``), not an ``/api``
route.

How this file connects to the project
--------------------------------------
- ``app/core/auth_dependencies.py`` supplies ``require_authenticated_user``.
- ``frontend-vite/src/context/AuthContext.jsx`` calls ``GET /auth/me`` on
  load and ``POST /auth/logout`` when the user signs out.
"""

from fastapi import APIRouter, Depends, Request

from core.auth_dependencies import require_authenticated_user
from db.models import User


router = APIRouter(
    prefix="/auth",
    tags=["auth"],
)


@router.get("/me")
def get_current_user(
    user: User = Depends(require_authenticated_user),
) -> dict:
    """
    Return the signed-in user's identity and role.

    Requires an existing session. The frontend treats a 401 response here as
    "not signed in" and re-navigates to the app root so the backend gate can
    send the browser to CILogon.
    """
    return {
        "id": user.id,
        "email": user.email,
        "name": user.name,
        "role": user.role,
    }


@router.post("/logout")
def logout(
    request: Request,
    _user: User = Depends(require_authenticated_user),
) -> dict:
    """
    Clear the local app session.

    This only ends the session for this app. It does not sign the person out
    of CILogon or their home institution.
    """
    request.session.clear()

    return {"logged_out": True}
