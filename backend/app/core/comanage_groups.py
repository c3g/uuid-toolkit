"""
COManage group-membership matching.

THE sole admission decision, as of the CILogon attribute-release fix
confirmed working end to end on 2026-08-28. ``app/core/oidc.py``'s
``process_callback()`` calls ``resolve_role_from_groups()`` on every login
and admits (or rejects) purely based on its answer -- a pre-existing row in
the app's own ``users`` table no longer grants access on its own; that
table is now just a synced mirror of who currently has access.

Confirmed live end to end: a fresh identity with COManage COU membership
but no prior ``users`` row logged in, resolved to ``"member"`` here from
its real ``groups`` claim, and was auto-enrolled on the spot.

Mirrors the pattern used by the SNV Benchmarking Dashboard's ``auth.R``
(a sibling C3G app already using COManage-sourced groups): filter the
``groups`` claim for strings containing this app's own COU name, then check
which role keyword is present.

``COU_NAME`` below was confirmed correct twice: once via COManage's own
"Manage Group Memberships" page, and again against a real ``groups`` claim
from CILogon showing the exact predicted strings (``CO:COU:c3g tech-dev
uuid-toolkit:admins``, ``:members:active``, ``:members:all``).
"""

COU_NAME = "c3g tech-dev uuid-toolkit"


def resolve_role_from_groups(
    groups: list[str] | None,
) -> str | None:
    """
    Decide a role from a CILogon ``groups`` claim, COManage-style.

    Filters for group strings that contain this app's own COU name, then
    checks which role keyword is present among the matches. An admin match
    takes priority if a person somehow shows up in both an admin group and
    a member group at once.

    Parameters
    ----------
    groups:
        The ``groups`` claim value from CILogon, if present. May be
        ``None`` or empty when the claim is missing or the person belongs
        to no groups at all.

    Returns
    -------
    str | None
        ``"admin"``, ``"member"``, or ``None`` when no group for this app's
        COU was found, or none of the matching groups carried a recognized
        role keyword.
    """
    if not groups:
        return None

    matching_groups = [
        group
        for group in groups
        if COU_NAME in group
    ]

    if not matching_groups:
        return None

    if any("admins" in group for group in matching_groups):
        return "admin"

    if any("members" in group for group in matching_groups):
        return "member"

    return None
