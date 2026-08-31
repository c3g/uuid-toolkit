"""
Repository functions for the app's local mirror of who has access.

COManage group membership (see ``app/core/comanage_groups.py``) is the
actual admission decision now, decided fresh on every login. This table no
longer grants access by itself -- it's a local, queryable record of who
currently has access and at what role, kept in sync by
``app/core/oidc.py``'s ``process_callback()`` on every successful login.
The read-only User Management page displays exactly this table.

How this file connects to the project
-------------------------------------
- ``db/models.py`` defines ``User``.
- ``app/core/oidc.py`` calls ``get_user_by_sub()``/``get_user_by_email()``
  to find an existing mirror row, ``bind_cilogon_sub()`` on someone's first
  login, ``create_user()`` to mirror a brand-new COManage-admitted person,
  and ``sync_role_from_comanage()`` to correct a mirrored role that no
  longer matches what COManage just reported.
- ``app/core/auth_dependencies.py`` calls ``get_user_by_id()`` on every
  protected request.
- ``app/api/users.py`` uses the list/update/delete functions for the
  admin-only (now display/cleanup-only, since COManage governs real
  access) user endpoints.
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


def sync_role_from_comanage(
    session: Session,
    *,
    user_id: int,
    role: str,
) -> User:
    """
    Overwrite an enrolled user's role to match what COManage just resolved.

    Unlike ``update_user_role()``, this has no last-admin guard: COManage is
    now the authoritative source for role, so a demotion it reports (even
    of the only admin on record here) must take effect, not be blocked by
    an app-side safety check meant for manual changes through the app's own
    (now display-only) admin UI. A no-op when the role already matches.
    """
    user = session.get(User, user_id)

    if user is None:
        raise ValueError(f"User {user_id} was not found.")

    if user.role != role:
        user.role = role
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
