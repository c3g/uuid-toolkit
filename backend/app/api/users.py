"""
Admin-only API routes for managing who is enrolled to use the application.

Every route in this router requires the admin role, enforced once at router
construction rather than on each function individually.

How this file connects to the project
--------------------------------------
- ``db/user_repository.py`` contains the actual enrollment queries and
  writes used here.
- ``app/core/auth_dependencies.py`` supplies ``require_admin``.
- ``api/database_management.py`` supplies ``require_confirmation()``, reused
  here for the delete route instead of duplicating it.
- A future admin-only "Manage Users" screen in the frontend would call
  these routes; the first admin account itself is created outside the app,
  by ``scripts/seed_admin.py``, since no admin exists yet to use this API.
"""

from fastapi import APIRouter, Depends, Form, HTTPException, Query
from sqlalchemy.orm import Session

from api.database_management import require_confirmation
from core.auth_dependencies import require_admin
from db.database import get_db_session
from db.models import User
from db.user_repository import (
    create_user,
    delete_user,
    list_users,
    update_user_role,
)


router = APIRouter(
    prefix="/users",
    tags=["users"],
    dependencies=[Depends(require_admin)],
)


def _serialize_user(user: User) -> dict:
    return {
        "id": user.id,
        "email": user.email,
        "name": user.name,
        "role": user.role,
        "created_at": user.created_at,
        "last_login_at": user.last_login_at,
    }


@router.get("")
def get_users(
    session: Session = Depends(get_db_session),
) -> list[dict]:
    """
    List every enrolled user.

    ``cilogon_sub`` is intentionally left out of the response since it is an
    internal identity token, not something the admin UI needs to display.
    """
    return [
        _serialize_user(user)
        for user in list_users(session)
    ]


@router.post("")
def add_user(
    email: str = Form(...),
    role: str = Form(...),
    name: str | None = Form(None),
    session: Session = Depends(get_db_session),
) -> dict:
    """
    Enroll a new user by email.

    Raises
    ------
    HTTPException
        400 when the role is invalid, the email is empty, or the email is
        already enrolled.
    """
    try:
        user = create_user(
            session,
            email=email,
            role=role,
            name=name,
        )

    except ValueError as error:
        raise HTTPException(
            status_code=400,
            detail=str(error),
        ) from error

    return _serialize_user(user)


@router.patch("/{user_id}")
def change_user_role(
    user_id: int,
    role: str = Form(...),
    session: Session = Depends(get_db_session),
) -> dict:
    """
    Change an enrolled user's role.

    Raises
    ------
    HTTPException
        400 when the role is invalid or the change would remove the last
        remaining admin.
    """
    try:
        user = update_user_role(
            session,
            user_id=user_id,
            role=role,
        )

    except ValueError as error:
        raise HTTPException(
            status_code=400,
            detail=str(error),
        ) from error

    return _serialize_user(user)


@router.delete("/{user_id}")
def remove_user(
    user_id: int,
    confirm: bool = Query(False),
    session: Session = Depends(get_db_session),
) -> dict:
    """
    Remove an enrolled user, revoking their access immediately.

    Raises
    ------
    HTTPException
        400 when confirmation is missing or the deletion would remove the
        last remaining admin.
        404 when the user does not exist.
    """
    require_confirmation(confirm)

    try:
        deleted = delete_user(
            session,
            user_id=user_id,
        )

    except ValueError as error:
        raise HTTPException(
            status_code=400,
            detail=str(error),
        ) from error

    if not deleted:
        raise HTTPException(
            status_code=404,
            detail=f"User {user_id} was not found.",
        )

    return {
        "user_id": user_id,
        "deleted": True,
    }
