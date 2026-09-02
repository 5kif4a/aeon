class TestAuth:
    async def test_missing_init_data_is_rejected(self, client):
        response = await client.get("/api/me")
        assert response.status_code == 401

    async def test_forged_init_data_is_rejected(self, client):
        headers = {"Authorization": "tma auth_date=1&hash=deadbeef&user=%7B%7D"}
        response = await client.get("/api/me", headers=headers)
        assert response.status_code == 401

    async def test_malformed_auth_date_is_rejected(self, client):
        headers = {"Authorization": "tma auth_date=not-a-number&hash=deadbeef&user=%7B%7D"}
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
        assert profile["plan"] == "Free"

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
        # Billing state is server-owned; arbitrary profile input cannot activate Pro.
        assert profile["plan"] == "Free"
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


class TestConversationStorage:
    async def test_agent_sessions_are_separate_and_messages_are_complete(
        self, client, auth_headers
    ):
        import sqlalchemy as sa

        from app.db.session import SessionFactory
        from app.services import conversations
        from tests.conftest import TEST_USER_ID

        assert (await client.get("/api/me", headers=auth_headers)).status_code == 200
        long_question = "Q" * 2000
        long_answer = "A" * 3900

        async with SessionFactory() as session:
            await conversations.start_session(session, TEST_USER_ID, "aurelius")
            await session.commit()
            await conversations.append_exchange(
                session, TEST_USER_ID, "aurelius", long_question, long_answer
            )

            await conversations.start_session(session, TEST_USER_ID, "machiavelli")
            await session.commit()
            await conversations.append_exchange(
                session, TEST_USER_ID, "machiavelli", "Strategy question", "Strategy answer"
            )

            await conversations.start_session(session, TEST_USER_ID, "aurelius")
            await session.commit()
            await conversations.append_exchange(
                session, TEST_USER_ID, "aurelius", "New session", "Fresh answer"
            )
            await conversations.append_completed_session(
                session, TEST_USER_ID, "council", "Council question", "Council answer"
            )

        async with SessionFactory() as session:
            aurelius_history = await conversations.list_history(
                session, TEST_USER_ID, "aurelius", limit=3
            )
            machiavelli_history = await conversations.list_history(
                session, TEST_USER_ID, "machiavelli", limit=3
            )
            overview_rows = (
                await session.execute(
                    sa.text(
                        "SELECT telegram_id, user_name, agent_id, status, message_count "
                        "FROM conversation_overview WHERE telegram_id = :user_id"
                    ),
                    {"user_id": TEST_USER_ID},
                )
            ).mappings().all()
            message_rows = (
                await session.execute(
                    sa.text(
                        "SELECT agent_id, role, text FROM conversation_messages_view "
                        "WHERE telegram_id = :user_id"
                    ),
                    {"user_id": TEST_USER_ID},
                )
            ).mappings().all()

        assert aurelius_history == [
            {"role": "user", "text": "New session"},
            {"role": "agent", "text": "Fresh answer"},
        ]
        assert machiavelli_history == []
        assert len(overview_rows) == 4
        assert all(row["telegram_id"] == TEST_USER_ID for row in overview_rows)
        assert all(row["user_name"] == "Tester" for row in overview_rows)
        assert sum(row["status"] == "active" for row in overview_rows) == 1
        assert sum(row["agent_id"] == "aurelius" for row in overview_rows) == 2
        assert sum(row["agent_id"] == "council" for row in overview_rows) == 1
        assert all(row["message_count"] == 2 for row in overview_rows)
        assert len(message_rows) == 8
        assert any(row["role"] == "user" and row["text"] == long_question for row in message_rows)
        assert any(row["role"] == "agent" and row["text"] == long_answer for row in message_rows)


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


class TestBilling:
    async def test_status_starts_as_free(self, client, auth_headers):
        response = await client.get("/api/billing/status", headers=auth_headers)
        assert response.status_code == 200
        status = response.json()
        assert status["plan"] == "Free"
        assert status["dailyLimit"] == 3
        assert status["canStartTrial"] is True
        assert status["proPriceStars"] == 299

    async def test_trial_can_only_start_once(self, client, auth_headers):
        started = await client.post("/api/billing/trial", headers=auth_headers)
        assert started.status_code == 200
        assert started.json()["plan"] == "Trial"
        assert started.json()["dailyLimit"] == 5

        repeated = await client.post("/api/billing/trial", headers=auth_headers)
        assert repeated.status_code == 409

    async def test_checkout_requires_running_bot(self, client, auth_headers):
        response = await client.post("/api/billing/checkout", headers=auth_headers)
        assert response.status_code == 503


class TestHealth:
    async def test_health(self, client):
        response = await client.get("/api/health")
        assert response.json() == {"status": "ok"}
