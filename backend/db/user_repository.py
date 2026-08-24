"""
Repository functions for enrolled application users.

This file contains the database queries and writes used to enroll, look up,
list, and remove the people allowed to use the application. Logging in
through CILogon proves identity; a row in this table is what actually grants
access, which is why every function here is careful about how a row is
found and changed.

How this file connects to the project
-------------------------------------
- ``db/models.py`` defines ``User``.
- ``app/core/oidc.py`` calls ``get_user_by_sub()`` and ``get_user_by_email()``
  during the login callback, and ``bind_cilogon_sub()`` the first time a
  pre-enrolled person logs in.
- ``app/core/auth_dependencies.py`` calls ``get_user_by_id()`` on every
  protected request.
- ``app/api/users.py`` uses the create/list/update/delete functions for the
  admin-only enrollment endpoints.
- ``scripts/seed_admin.py`` uses ``get_user_by_email()`` and
  ``create_user()``/``update_user_role()`` to create the first admin account.
- ``db/database.py`` provides the SQLAlchemy session.

Adding a new role
------------------
There are currently exactly two roles, ``"admin"`` and ``"member"``, listed in
``ALLOWED_ROLES`` below. A new role only needs a change here (and in the
frontend's role-based UI checks) since ``role`` is stored as a plain string,
not a database enum.
"""

from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from db.models import User


ALLOWED_ROLES = {"admin", "member"}


def get_user_by_sub(
    session: Session,
    *,
    cilogon_sub: str,
) -> User | None:
    """
    Find an enrolled user by their CILogon ``sub`` claim.

    This is the authoritative lookup used on every login once a person has
    logged in at least once before.
    """
    statement = select(User).where(
        User.cilogon_sub == cilogon_sub
    )

    return session.execute(
        statement
    ).scalar_one_or_none()


def get_user_by_email(
    session: Session,
    *,
    email: str,
) -> User | None:
    """
    Find an enrolled user by email.

    Used for admin enrollment lookups and for matching a pre-enrolled row
    (``cilogon_sub`` still empty) on someone's first successful login.
    """
    cleaned_email = email.strip().lower()

    statement = select(User).where(
        func.lower(User.email) == cleaned_email
    )

    return session.execute(
        statement
    ).scalar_one_or_none()


def get_user_by_id(
    session: Session,
    *,
    user_id: int,
) -> User | None:
    """
    Return one enrolled user by their database ID.

    Called on every protected request to re-derive the current role from the
    database rather than trusting anything stored in the session cookie.
    """
    return session.get(User, user_id)


def list_users(
    session: Session,
) -> list[User]:
    """
    Return every enrolled user ordered by database row ID.
    """
    statement = select(User).order_by(User.id)

    return list(
        session.execute(statement).scalars().all()
    )


def count_admins(
    session: Session,
) -> int:
    """
    Return how many enrolled users currently have the admin role.

    Used before removing or demoting an admin so the last admin account can
    never be deleted or demoted, which would lock everyone out of
    Database Management and user enrollment.
    """
    statement = select(func.count()).select_from(
        User
    ).where(User.role == "admin")

    return session.execute(statement).scalar_one()


def create_user(
    session: Session,
    *,
    email: str,
    role: str,
    name: str | None = None,
    cilogon_sub: str | None = None,
) -> User:
    """
    Enroll a new user by email.

    Parameters
    ----------
    email:
        The email address the person will log in with. Enrollment is
        matched by email until their first successful login, after which
        ``cilogon_sub`` becomes the authoritative identity key.

    role:
        Either ``"admin"`` or ``"member"``.

    Raises
    ------
    ValueError
        Raised when the role is not recognized, the email is empty, or the
        email already belongs to an enrolled user.
    """
    cleaned_email = email.strip().lower()

    if not cleaned_email:
        raise ValueError("Email cannot be empty.")

    if role not in ALLOWED_ROLES:
        raise ValueError(
            f"Role '{role}' is not recognized. "
            f"Allowed roles: {sorted(ALLOWED_ROLES)}."
        )

    user = User(
        email=cleaned_email,
        role=role,
        name=name.strip() if name else None,
        cilogon_sub=cilogon_sub,
    )

    try:
        session.add(user)
        session.commit()
        session.refresh(user)

    except IntegrityError as error:
        session.rollback()

        raise ValueError(
            f"A user with email '{cleaned_email}' "
            "is already enrolled."
        ) from error

    return user


def bind_cilogon_sub(
    session: Session,
    *,
    user_id: int,
    cilogon_sub: str,
) -> User:
    """
    Attach a CILogon ``sub`` claim to a pre-enrolled user row.

    Called once, the first time a person who was enrolled by email logs in
    successfully. Every later login is looked up by ``cilogon_sub`` instead.
    """
    user = session.get(User, user_id)

    if user is None:
        raise ValueError(f"User {user_id} was not found.")

    user.cilogon_sub = cilogon_sub

    session.commit()
    session.refresh(user)

    return user


def touch_last_login(
    session: Session,
    *,
    user_id: int,
) -> None:
    """
    Record that a user just logged in successfully.
    """
    user = session.get(User, user_id)

    if user is None:
        return

    user.last_login_at = func.now()

    session.commit()


def update_user_role(
    session: Session,
    *,
    user_id: int,
    role: str,
) -> User:
    """
    Change an enrolled user's role.

    Raises
    ------
    ValueError
        Raised when the role is not recognized, the user does not exist, or
        the change would remove the last remaining admin.
    """
    if role not in ALLOWED_ROLES:
        raise ValueError(
            f"Role '{role}' is not recognized. "
            f"Allowed roles: {sorted(ALLOWED_ROLES)}."
        )

    user = session.get(User, user_id)

    if user is None:
        raise ValueError(f"User {user_id} was not found.")

    if (
        user.role == "admin"
        and role != "admin"
        and count_admins(session) <= 1
    ):
        raise ValueError(
            "Cannot change the role of the last remaining admin."
        )

    user.role = role

    session.commit()
    session.refresh(user)

    return user


def delete_user(
    session: Session,
    *,
    user_id: int,
) -> bool:
    """
    Remove an enrolled user, revoking their access immediately.

    Returns
    -------
    bool
        ``True`` when a user was deleted, ``False`` when the user did not
        exist.

    Raises
    ------
    ValueError
        Raised when deleting this user would remove the last remaining
        admin.
    """
    user = session.get(User, user_id)

    if user is None:
        return False

    if user.role == "admin" and count_admins(session) <= 1:
        raise ValueError(
            "Cannot delete the last remaining admin."
        )

    session.delete(user)
    session.commit()

    return True
