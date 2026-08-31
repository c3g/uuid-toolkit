"""
Tests for the (not-yet-wired-in) COManage group matcher.

The group strings used here are mock data, shaped after the SNV
Benchmarking Dashboard's real, working pattern with the UUID Toolkit's own
(unconfirmed) COU name substituted in -- not real values seen from CILogon.
See core/comanage_groups.py's module docstring for the full context.
"""

from core.comanage_groups import resolve_role_from_groups


# Modeled on the real group list Soofia's SNV dashboard receives, with
# "snv-benchmarking-dashboard" swapped for our own (unconfirmed) COU name.
UUID_TOOLKIT_ADMIN_GROUPS = [
    "CO:members:all",
    "CO:members:active",
    "CO:COU:c3g tech-dev uuid-toolkit:members:active",
    "CO:COU:c3g tech-dev uuid-toolkit:members:all",
    "CO:COU:c3g tech-dev uuid-toolkit:admins",
]

UUID_TOOLKIT_MEMBER_GROUPS = [
    "CO:members:all",
    "CO:members:active",
    "CO:COU:c3g tech-dev uuid-toolkit:members:active",
    "CO:COU:c3g tech-dev uuid-toolkit:members:all",
]

# Someone enrolled in a different app's COU entirely -- should never match
# ours, even though the shape of the strings is identical.
SNV_ONLY_GROUPS = [
    "CO:members:all",
    "CO:members:active",
    "CO:COU:c3g tech-dev snv-benchmarking-dashboard:members:active",
    "CO:COU:c3g tech-dev snv-benchmarking-dashboard:members:all",
    "CO:COU:c3g tech-dev snv-benchmarking-dashboard:admins",
]


def test_no_groups_claim_resolves_to_no_role():
    assert resolve_role_from_groups(None) is None


def test_empty_groups_list_resolves_to_no_role():
    assert resolve_role_from_groups([]) is None


def test_admin_group_resolves_to_admin():
    assert (
        resolve_role_from_groups(UUID_TOOLKIT_ADMIN_GROUPS)
        == "admin"
    )


def test_member_only_groups_resolves_to_member():
    assert (
        resolve_role_from_groups(UUID_TOOLKIT_MEMBER_GROUPS)
        == "member"
    )


def test_unrelated_apps_groups_do_not_match():
    assert resolve_role_from_groups(SNV_ONLY_GROUPS) is None


def test_collaboration_wide_groups_alone_do_not_grant_a_role():
    # Being a member of the overall CO ("CO:members:all") without being in
    # this app's specific COU should not, on its own, grant any role.
    assert (
        resolve_role_from_groups(
            ["CO:members:all", "CO:members:active"]
        )
        is None
    )


def test_admin_takes_priority_when_both_roles_present():
    groups = UUID_TOOLKIT_MEMBER_GROUPS + [
        "CO:COU:c3g tech-dev uuid-toolkit:admins"
    ]

    assert resolve_role_from_groups(groups) == "admin"
