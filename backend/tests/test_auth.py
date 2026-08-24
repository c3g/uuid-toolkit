"""
Tests for the login gate and role-based route protection.

These tests use dependency overrides (`anonymous_client`, `member_client`,
`admin_client` from `conftest.py`) for the permission matrix, and targeted
monkeypatching of `main.process_callback` / `main.redirect_to_cilogon` for
the callback and redirect flows -- no real network call to CILogon is made
anywhere in this file.
"""


# ---------------------------------------------------------------------
# Route-permission matrix
# ---------------------------------------------------------------------

def test_projects_requires_authentication(anonymous_client):
    response = anonymous_client.get("/api/projects")
    assert response.status_code == 401


def test_projects_allows_member(member_client):
    response = member_client.get("/api/projects")
    assert response.status_code == 200


def test_projects_allows_admin(admin_client):
    response = admin_client.get("/api/projects")
    assert response.status_code == 200


def test_identifier_database_requires_authentication(anonymous_client):
    response = anonymous_client.get("/api/identifier_database")
    assert response.status_code == 401


def test_identifier_database_forbidden_for_member(member_client):
    response = member_client.get("/api/identifier_database")
    assert response.status_code == 403


def test_identifier_database_allowed_for_admin(admin_client):
    response = admin_client.get("/api/identifier_database")
    assert response.status_code == 200


def test_users_requires_authentication(anonymous_client):
    response = anonymous_client.get("/api/users")
    assert response.status_code == 401


def test_users_forbidden_for_member(member_client):
    response = member_client.get("/api/users")
    assert response.status_code == 403


def test_users_allowed_for_admin(admin_client):
    response = admin_client.get("/api/users")
    assert response.status_code == 200


def test_auth_me_requires_authentication(anonymous_client):
    response = anonymous_client.get("/api/auth/me")
    assert response.status_code == 401


def test_auth_me_returns_identity_for_member(member_client):
    response = member_client.get("/api/auth/me")
    assert response.status_code == 200
    assert response.json()["role"] == "member"


def test_health_and_ready_do_not_require_authentication(anonymous_client):
    assert anonymous_client.get("/api/health").status_code == 200
    assert anonymous_client.get("/api/ready").status_code == 200


# ---------------------------------------------------------------------
# Callback flow (GET / with ?code&state)
# ---------------------------------------------------------------------

def test_callback_rejects_unenrolled_user(client, monkeypatch):
    import main
    from core.oidc import UnenrolledUserError

    async def fake_process_callback(request, session):
        raise UnenrolledUserError("nobody@example.com")

    monkeypatch.setattr(main, "process_callback", fake_process_callback)

    response = client.get("/?code=abc&state=xyz", follow_redirects=False)

    assert response.status_code == 403
    assert "nobody@example.com" in response.text
    assert "uuid_toolkit_session" not in client.cookies


def test_callback_enrolls_and_persists_session(client, monkeypatch):
    import main
    from core.auth_dependencies import require_admin, require_authenticated_user

    # Enroll a user through the real admin API first (the `client` fixture
    # defaults to an authenticated admin identity).
    enroll_response = client.post(
        "/api/users",
        data={
            "email": "person@example.com",
            "role": "member",
            "name": "Person",
        },
    )
    assert enroll_response.status_code == 200
    enrolled_user_id = enroll_response.json()["id"]

    async def fake_process_callback(request, session):
        from db.user_repository import get_user_by_email

        return get_user_by_email(session, email="person@example.com")

    monkeypatch.setattr(main, "process_callback", fake_process_callback)

    response = client.get("/?code=abc&state=xyz", follow_redirects=False)

    assert response.status_code == 302
    assert response.headers["location"] == "/"
    assert "uuid_toolkit_session" in client.cookies

    # Prove the session cookie actually works against the real
    # `require_authenticated_user`, not a dependency override -- this is
    # the one check that exercises `SessionMiddleware` and the database
    # lookup together, end to end.
    main.app.dependency_overrides.pop(require_authenticated_user, None)
    main.app.dependency_overrides.pop(require_admin, None)

    me_response = client.get("/api/auth/me")

    assert me_response.status_code == 200
    assert me_response.json()["id"] == enrolled_user_id
    assert me_response.json()["email"] == "person@example.com"


# ---------------------------------------------------------------------
# Redirect to CILogon
# ---------------------------------------------------------------------

def test_root_redirects_unauthenticated_visitor_to_cilogon(
    client,
    monkeypatch,
):
    import main
    from core.auth_dependencies import require_admin, require_authenticated_user
    from starlette.responses import RedirectResponse

    async def fake_redirect_to_cilogon(request):
        # A stand-in for Authlib's real redirect, which would otherwise
        # need a live network call to CILogon's discovery endpoint.
        return RedirectResponse(
            "https://cilogon.org/authorize?fake=1",
            status_code=302,
        )

    monkeypatch.setattr(
        main,
        "redirect_to_cilogon",
        fake_redirect_to_cilogon,
    )

    main.app.dependency_overrides.pop(require_authenticated_user, None)
    main.app.dependency_overrides.pop(require_admin, None)

    response = client.get("/", follow_redirects=False)

    assert response.status_code == 302
    assert response.headers["location"].startswith(
        "https://cilogon.org/"
    )
