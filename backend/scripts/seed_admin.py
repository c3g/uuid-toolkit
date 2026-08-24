import argparse

from db.database import SessionLocal
from db.user_repository import (
    create_user,
    get_user_by_email,
    update_user_role,
)


def main() -> None:
    parser = argparse.ArgumentParser(
        description=(
            "Create the first admin account, or promote an "
            "already-enrolled user to admin. Run this once, directly on "
            "the server, since the admin-only enrollment API cannot be "
            "used before an admin exists."
        )
    )
    parser.add_argument(
        "--email",
        required=True,
        help="Email address the admin will log in with.",
    )
    parser.add_argument(
        "--name",
        default=None,
        help="Optional display name.",
    )

    args = parser.parse_args()

    session = SessionLocal()

    try:
        existing_user = get_user_by_email(
            session,
            email=args.email,
        )

        if existing_user is None:
            user = create_user(
                session,
                email=args.email,
                role="admin",
                name=args.name,
            )
            print(f"Created admin user: {user.email}")

        else:
            user = update_user_role(
                session,
                user_id=existing_user.id,
                role="admin",
            )
            print(f"Promoted existing user to admin: {user.email}")

    finally:
        session.close()


if __name__ == "__main__":
    main()
