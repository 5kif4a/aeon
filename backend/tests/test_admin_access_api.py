"""Postgres-backed tests for /api/admin/access: roles, grants and what each role may do."""

import pytest
from sqlalchemy import delete

from app.db.models import AdminRole, User
from app.db.session import SessionFactory
from tests.conftest import build_init_data, make_admin

OWNER_ID = 900_000_501  # seeded as owner in the database
SUPPORT_ID = 900_000_502
STRANGER_ID = 900_000_503
CUSTOM_ROLE = "analyst-test"


def headers_for(user_id: int, name: str = "Admin") -> dict:
    return {"Authorization": f"tma {build_init_data(user_id=user_id, name=name)}"}


@pytest.fixture(autouse=True)
async def access_fixture():
    await make_admin(OWNER_ID, "owner", "Owner")
    async with SessionFactory() as session:
        session.add_all(
            [
                User(id=SUPPORT_ID, language="ru", name="Support"),
                User(id=STRANGER_ID, language="en", name="Stranger"),
            ]
        )
        await session.commit()
    yield
    async with SessionFactory() as session:
        # admin_accounts rows go with the users (FK ON DELETE CASCADE).
        await session.execute(delete(User).where(User.id.in_([OWNER_ID, SUPPORT_ID, STRANGER_ID])))
        await session.execute(delete(AdminRole).where(AdminRole.id == CUSTOM_ROLE))
        await session.commit()


async def test_stored_owner_sees_the_whole_matrix(client):
    response = await client.get("/api/admin/access", headers=headers_for(OWNER_ID))
    assert response.status_code == 200, response.text
    body = response.json()
    assert {"stats.view", "admins.manage"} <= {p["key"] for p in body["permissions"]}
    assert {"owner", "support", "marketing"} <= {role["id"] for role in body["roles"]}
    owner_row = next(row for row in body["admins"] if row["userId"] == OWNER_ID)
    assert owner_row["roleId"] == "owner"

    me = await client.get("/api/admin/me", headers=headers_for(OWNER_ID))
    assert me.json()["isOwner"] is True and me.json()["permissions"] == ["*"]


async def test_granted_role_decides_what_the_admin_can_reach(client):
    owner = headers_for(OWNER_ID)
    support = headers_for(SUPPORT_ID, "Support")

    assert (await client.get("/api/admin/me", headers=support)).status_code == 403

    granted = await client.post(
        "/api/admin/access/admins",
        json={"userId": SUPPORT_ID, "roleId": "support", "note": "on duty"},
        headers=owner,
    )
    assert granted.status_code == 200, granted.text
    assert granted.json()["roleId"] == "support"

    me = await client.get("/api/admin/me", headers=support)
    assert me.status_code == 200 and me.json()["isOwner"] is False
    assert "conversations.view" in me.json()["permissions"]

    # In scope for support...
    assert (await client.get("/api/admin/conversations", headers=support)).status_code == 200
    # ...and out of scope: no audience tooling, no access management.
    assert (await client.get("/api/admin/segments", headers=support)).status_code == 403
    forbidden = await client.get("/api/admin/access", headers=support)
    assert forbidden.status_code == 403 and "admins.view" in forbidden.json()["detail"]

    revoked = await client.delete(f"/api/admin/access/admins/{SUPPORT_ID}", headers=owner)
    assert revoked.status_code == 204
    assert (await client.get("/api/admin/me", headers=support)).status_code == 403


async def test_marketing_role_sends_broadcasts_but_reads_no_dialogues(client):
    owner = headers_for(OWNER_ID)
    marketer = headers_for(SUPPORT_ID, "Marketer")
    await client.post(
        "/api/admin/access/admins",
        json={"userId": SUPPORT_ID, "roleId": "marketing"},
        headers=owner,
    )
    assert (await client.get("/api/admin/segments", headers=marketer)).status_code == 200
    assert (await client.get("/api/admin/broadcasts", headers=marketer)).status_code == 200
    assert (await client.get("/api/admin/conversations", headers=marketer)).status_code == 403
    assert (await client.get("/api/admin/payments", headers=marketer)).status_code == 403


async def test_grants_are_guarded_against_lockouts_and_ghost_users(client):
    owner = headers_for(OWNER_ID)

    # Unknown Telegram id: a grant must not fabricate a user row (it would fake a signup).
    unknown = await client.post(
        "/api/admin/access/admins", json={"userId": 900_000_599, "roleId": "support"}, headers=owner
    )
    assert unknown.status_code == 422 and "open the bot" in unknown.json()["detail"]

    for payload in (
        {"userId": OWNER_ID, "roleId": "support"},  # own access
        {"userId": SUPPORT_ID, "roleId": "nope"},  # unknown role
    ):
        assert (
            await client.post("/api/admin/access/admins", json=payload, headers=owner)
        ).status_code == 422

    # Own access and a user who is not an admin at all.
    assert (
        await client.delete(f"/api/admin/access/admins/{OWNER_ID}", headers=owner)
    ).status_code == 422
    assert (
        await client.delete(f"/api/admin/access/admins/{STRANGER_ID}", headers=owner)
    ).status_code == 422


async def test_last_manager_cannot_be_revoked_or_demoted():
    """What replaces the env allowlist, checked at the service level.

    Through the API this is unreachable - an admin can neither change their own access nor
    re-cut their own role, so the caller always remains a manager. The invariant is the
    backstop for everything else (a script, a future relaxation of those rules).
    """
    from app.services import admin_access

    await make_admin(OWNER_ID, "owner", "Owner")
    async with SessionFactory() as session:
        with pytest.raises(admin_access.AccessError, match="manage access"):
            await admin_access.revoke_admin(session, OWNER_ID, actor_id=SUPPORT_ID)

        # Moving the only manager into a role without `admins.manage` is refused too.
        with pytest.raises(admin_access.AccessError, match="manage access"):
            await admin_access.grant_admin(
                session, OWNER_ID, role_id="support", actor_id=SUPPORT_ID
            )

    # With a second manager in place the same revoke goes through.
    await make_admin(SUPPORT_ID, "owner", "Second owner")
    async with SessionFactory() as session:
        await admin_access.revoke_admin(session, OWNER_ID, actor_id=SUPPORT_ID)
        assert {row.user_id for row in await admin_access.list_admins(session)} == {SUPPORT_ID}

    # Stripping `admins.manage` from the only role that grants it is refused as well. The
    # built-in owner role is locked, so this needs a custom one.
    async with SessionFactory() as session:
        await admin_access.create_role(
            session,
            role_id=CUSTOM_ROLE,
            title="Manager",
            description="",
            permissions=["admins.manage"],
            actor_id=SUPPORT_ID,
        )
        await admin_access.grant_admin(session, OWNER_ID, role_id=CUSTOM_ROLE, actor_id=SUPPORT_ID)
        await admin_access.revoke_admin(session, SUPPORT_ID, actor_id=OWNER_ID)
        with pytest.raises(admin_access.AccessError, match="manage access"):
            await admin_access.update_role(
                session,
                CUSTOM_ROLE,
                title=None,
                description=None,
                permissions=["stats.view"],
                actor_id=SUPPORT_ID,
            )


async def test_custom_role_lifecycle(client):
    owner = headers_for(OWNER_ID)

    created = await client.post(
        "/api/admin/access/roles",
        json={
            "id": CUSTOM_ROLE,
            "title": "Analyst",
            "description": "Reads numbers",
            "permissions": ["stats.view", "users.view"],
        },
        headers=owner,
    )
    assert created.status_code == 200, created.text
    assert created.json()["permissions"] == ["stats.view", "users.view"]

    updated = await client.put(
        f"/api/admin/access/roles/{CUSTOM_ROLE}",
        json={"permissions": ["stats.view"]},
        headers=owner,
    )
    assert updated.status_code == 200 and updated.json()["permissions"] == ["stats.view"]

    # An unknown permission key is a typo, not an empty role.
    assert (
        await client.put(
            f"/api/admin/access/roles/{CUSTOM_ROLE}",
            json={"permissions": ["users.delete"]},
            headers=owner,
        )
    ).status_code == 422
    # Built-in roles stay; the owner role keeps every permission.
    assert (
        await client.delete("/api/admin/access/roles/support", headers=owner)
    ).status_code == 422
    assert (
        await client.put(
            "/api/admin/access/roles/owner", json={"permissions": ["stats.view"]}, headers=owner
        )
    ).status_code == 422

    # A role still held by someone cannot be deleted.
    await client.post(
        "/api/admin/access/admins",
        json={"userId": SUPPORT_ID, "roleId": CUSTOM_ROLE},
        headers=owner,
    )
    assert (
        await client.delete(f"/api/admin/access/roles/{CUSTOM_ROLE}", headers=owner)
    ).status_code == 422
    await client.delete(f"/api/admin/access/admins/{SUPPORT_ID}", headers=owner)
    assert (
        await client.delete(f"/api/admin/access/roles/{CUSTOM_ROLE}", headers=owner)
    ).status_code == 204
