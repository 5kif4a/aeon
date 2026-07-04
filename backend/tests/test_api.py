class TestAuth:
    async def test_missing_init_data_is_rejected(self, client):
        response = await client.get("/api/me")
        assert response.status_code == 401

    async def test_forged_init_data_is_rejected(self, client):
        headers = {"Authorization": "tma auth_date=1&hash=deadbeef&user=%7B%7D"}
        response = await client.get("/api/me", headers=headers)
        assert response.status_code == 401


class TestProfile:
    async def test_me_creates_user_from_init_data(self, client, auth_headers):
        response = await client.get("/api/me", headers=auth_headers)
        assert response.status_code == 200
        profile = response.json()
        assert profile["name"] == "Tester"
        # language_code "ru" from initData normalizes to a supported language
        assert profile["language"] == "ru"
        assert profile["plan"] == "Basic"

    async def test_patch_updates_profile_and_computes_age(self, client, auth_headers):
        response = await client.patch(
            "/api/me",
            headers=auth_headers,
            json={"name": "Renée ✓", "birthDate": "1995-05-18", "plan": "Pro"},
        )
        assert response.status_code == 200
        profile = response.json()
        # non-ASCII round-trips cleanly through JSON + Postgres
        assert profile["name"] == "Renée ✓"
        assert profile["plan"] == "Pro"
        assert isinstance(profile["age"], int) and profile["age"] >= 29

    async def test_patch_rejects_unsupported_language(self, client, auth_headers):
        response = await client.patch("/api/me", headers=auth_headers, json={"language": "fr"})
        assert response.status_code == 422

    async def test_patch_accepts_supported_language(self, client, auth_headers):
        response = await client.patch("/api/me", headers=auth_headers, json={"language": "en"})
        assert response.status_code == 200
        assert response.json()["language"] == "en"


class TestGoal:
    async def test_goal_lifecycle(self, client, auth_headers):
        assert (await client.get("/api/goal", headers=auth_headers)).json() is None

        created = await client.post(
            "/api/goal", headers=auth_headers, json={"text": "finish the project"}
        )
        assert created.status_code == 200
        assert created.json()["status"] == "active"

        active = (await client.get("/api/goal", headers=auth_headers)).json()
        assert active["text"] == "finish the project"

        closed = await client.post("/api/goal/close", headers=auth_headers)
        assert closed.json()["status"] == "closed"
        assert (await client.get("/api/goal", headers=auth_headers)).json() is None

    async def test_new_goal_replaces_active_one(self, client, auth_headers):
        await client.post("/api/goal", headers=auth_headers, json={"text": "first"})
        await client.post("/api/goal", headers=auth_headers, json={"text": "second"})
        active = (await client.get("/api/goal", headers=auth_headers)).json()
        assert active["text"] == "second"

    async def test_close_without_active_goal_is_404(self, client, auth_headers):
        response = await client.post("/api/goal/close", headers=auth_headers)
        assert response.status_code == 404


class TestDiary:
    async def test_diary_lifecycle(self, client, auth_headers):
        created = await client.post(
            "/api/diary", headers=auth_headers, json={"text": "Today I realized..."}
        )
        assert created.status_code == 200
        entry_id = created.json()["id"]

        entries = (await client.get("/api/diary", headers=auth_headers)).json()
        assert [entry["id"] for entry in entries] == [entry_id]

        deleted = await client.delete(f"/api/diary/{entry_id}", headers=auth_headers)
        assert deleted.status_code == 204
        assert (await client.get("/api/diary", headers=auth_headers)).json() == []

    async def test_delete_unknown_entry_is_404(self, client, auth_headers):
        response = await client.delete(
            "/api/diary/00000000-0000-0000-0000-000000000000", headers=auth_headers
        )
        assert response.status_code == 404


class TestAgents:
    async def test_agents_list(self, client, auth_headers):
        response = await client.get("/api/agents", headers=auth_headers)
        assert [agent["id"] for agent in response.json()] == ["aurelius", "machiavelli", "jung"]

    async def test_dialog_without_running_bot_is_503(self, client, auth_headers):
        response = await client.post("/api/agents/aurelius/dialog", headers=auth_headers, json={})
        assert response.status_code == 503

    async def test_dialog_with_unknown_agent_is_400(self, client, auth_headers):
        response = await client.post("/api/agents/socrates/dialog", headers=auth_headers, json={})
        assert response.status_code == 400


class TestHealth:
    async def test_health(self, client):
        response = await client.get("/api/health")
        assert response.json() == {"status": "ok"}
