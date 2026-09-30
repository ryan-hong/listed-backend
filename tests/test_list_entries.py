"""Exercise HTTP routes against an isolated SQLite database.

The sync-session adapter avoids adding a production SQLite driver dependency.
PostgreSQL row locks and named unique-constraint errors are checked separately.
"""

import asyncio
import json
import unittest
import uuid
from datetime import datetime, timezone
from unittest.mock import AsyncMock, Mock

from fastapi import FastAPI, HTTPException
from fastapi.exceptions import RequestValidationError
from fastapi.testclient import TestClient
from sqlalchemy import BigInteger, MetaData, create_engine, event, inspect, select, text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.compiler import compiles
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool
from sqlalchemy.schema import DefaultClause

from listed_backend.database import Base, get_db
from listed_backend.dependencies.auth import get_current_user
from listed_backend.models.list import List
from listed_backend.models.list_entry import EntryLog, EntryMedia, ListEntry
from listed_backend.models.user import User
from listed_backend.routers.list_entries import router
from listed_backend.schemas.list_entry import ListEntryUpdate
from listed_backend.schemas.validation import json_safe_validation_handler
from listed_backend.services.list_entries import get_owned
from listed_backend.services.list_entries import _commit, update


@compiles(BigInteger, "sqlite")
def sqlite_integer(type_, compiler, **kw):
    return "INTEGER"


@compiles(JSONB, "sqlite")
def sqlite_json(type_, compiler, **kw):
    return "JSON"


class AsyncTestSession:
    def __init__(self, session):
        self.session = session

    def add(self, obj):
        self.session.add(obj)

    async def execute(self, statement):
        return self.session.execute(statement)

    async def commit(self):
        self.session.commit()

    async def rollback(self):
        self.session.rollback()

    async def refresh(self, obj, **kwargs):
        self.session.refresh(obj, **kwargs)
        if isinstance(obj, EntryLog):
            assert "media" not in inspect(obj).unloaded, "Response would trigger async lazy loading"

    async def delete(self, obj):
        self.session.delete(obj)


class EntryEndpointTests(unittest.TestCase):
    def setUp(self):
        self.engine = create_engine("sqlite://", poolclass=StaticPool, connect_args={"check_same_thread": False})

        @event.listens_for(self.engine, "connect")
        def setup_sqlite(connection, record):
            connection.execute("PRAGMA foreign_keys=ON")
            connection.create_function("now", 0, lambda: datetime.now(timezone.utc).isoformat())

        metadata = MetaData()
        for table in Base.metadata.sorted_tables:
            table.to_metadata(metadata)
        metadata.tables["list_entries"].c.meta.server_default = DefaultClause(text("'{}'"))
        metadata.create_all(self.engine)
        self.user_id = uuid.uuid4()
        self.other_id = uuid.uuid4()
        with Session(self.engine) as session:
            session.add_all([User(id=self.user_id, email="owner@example.com"), User(id=self.other_id, email="other@example.com")])
            session.flush()
            session.add_all([List(id=1, user_id=self.user_id, name="Mine"), List(id=2, user_id=self.other_id, name="Other"), List(id=3, user_id=self.user_id, name="Another")])
            session.commit()

        def database():
            with Session(self.engine, expire_on_commit=False) as session:
                yield AsyncTestSession(session)

        app = FastAPI()
        app.add_exception_handler(RequestValidationError, json_safe_validation_handler)
        app.include_router(router)
        app.dependency_overrides[get_db] = database
        app.dependency_overrides[get_current_user] = lambda: User(id=self.user_id, email="owner@example.com")
        self.client = TestClient(app)

    def tearDown(self):
        self.client.close()
        self.engine.dispose()

    def create(self, **fields):
        body = {"entry_type": "MOVIE", "title": "Film", "log": {"rating": 8.9}, **fields}
        return self.client.post("/lists/1/entries", json=body)

    def test_create_get_update_add_log_delete(self):
        response = self.create(meta={"genres": [" Drama ", "drama"]})
        self.assertEqual(response.status_code, 201, response.text)
        entry = response.json()
        path = f"/lists/1/entries/{entry['id']}"
        self.assertEqual(entry["log_count"], 1)
        self.assertEqual(entry["position"], 0)
        self.assertEqual(entry["meta"], {"genres": ["Drama"]})
        self.assertEqual(entry["logs"][0]["rating"], 8.9)
        self.assertEqual(entry["logs"][0]["media"], [])
        self.assertEqual(self.create().json()["position"], 1)
        response = self.client.post(path + "/logs", json={"note": " Watched again "})
        self.assertEqual(response.status_code, 201, response.text)
        self.assertEqual(response.json()["note"], "Watched again")
        fetched = self.client.get(path).json()
        self.assertEqual(fetched["log_count"], 2)
        self.assertEqual(len(fetched["logs"]), 2)
        response = self.client.patch(path, json={"title": "New title", "is_favourited": True})
        self.assertEqual(response.status_code, 200, response.text)
        self.assertEqual(response.json()["meta"], {"genres": ["Drama"]})
        self.assertEqual(response.json()["title"], "New title")
        # Seed media to check response loading and the entire deletion cascade.
        with Session(self.engine) as session:
            session.add(EntryMedia(log_id=entry["logs"][0]["id"], url="https://example.com/photo.jpg", media_type="image"))
            session.commit()
        self.assertEqual(len(self.client.get(path).json()["logs"][-1]["media"]), 1)
        self.assertEqual(self.client.delete(path).status_code, 204)
        self.assertEqual(self.client.get(path).status_code, 404)
        with Session(self.engine) as session:
            self.assertEqual(session.scalars(select(EntryLog).where(EntryLog.entry_id == entry["id"])).all(), [])
            self.assertEqual(session.scalars(select(EntryMedia)).all(), [])

    def test_ownership_and_list_scope(self):
        entry_id = self.create().json()["id"]
        for list_id in (2, 3, 999):
            path = f"/lists/{list_id}/entries/{entry_id}"
            self.assertEqual(self.client.get(path).status_code, 404)
            self.assertEqual(self.client.patch(path, json={"title": "Forbidden"}).status_code, 404)
            self.assertEqual(self.client.delete(path).status_code, 404)
            self.assertEqual(self.client.post(path + "/logs", json={"rating": 5}).status_code, 404)
        self.assertEqual(self.client.post("/lists/2/entries", json={"entry_type": "MOVIE", "title": "Film", "log": {"note": "test"}}).status_code, 404)

    def test_required_log_and_rating_validation(self):
        for rating in (1, 1.1, 8.9, 10):
            with self.subTest(rating=rating):
                self.assertEqual(self.create(log={"rating": rating}).status_code, 201)
        for log in ({}, {"note": " "}, {"rating": 8.95}, {"rating": 0.9}, {"rating": 10.1}, {"rating": True}, {"rating": "8.9"}, {"occurred_at": "2026-01-01T00:00:00"}):
            with self.subTest(log=log):
                self.assertEqual(self.create(log=log).status_code, 422)
        self.assertEqual(self.create(log={"occurred_at": "2026-01-01T00:00:00Z"}).status_code, 201)
        response = self.client.post("/lists/1/entries", json={"entry_type": "MOVIE", "title": "Film"})
        self.assertEqual(response.status_code, 422)

    def test_metadata_update_contract_and_atomic_validation(self):
        entry = self.create(meta={"directors": ["Director"], "release_year": 2025}).json()
        path = f"/lists/1/entries/{entry['id']}"
        invalid = [
            ({"entry_type": "BOOK"}, ["body", "meta"]),
            ({"meta": {"release_year": "2025"}}, ["body", "meta", "release_year"]),
            ({"entry_type": "PLACE", "meta": {"latitude": 0}}, ["body", "meta", "longitude"]),
            ({"entry_type": "movie"}, ["body", "entry_type"]),
            ({"meta": {"unknown": None}}, ["body", "meta", "unknown"]),
            ({"list_id": 3}, ["body", "list_id"]),
            ({"title": None}, ["body", "title"]),
        ]
        for body, location in invalid:
            with self.subTest(body=body):
                response = self.client.patch(path, json=body)
                self.assertEqual(response.status_code, 422, response.text)
                self.assertEqual(response.json()["detail"][0]["loc"], location)
                self.assertEqual(self.client.get(path).json()["meta"], entry["meta"])
        response = self.client.patch(path, json={"meta": {"genres": []}})
        self.assertEqual(response.json()["meta"], {"genres": []})
        self.assertEqual(self.client.patch(path, json={"meta": None}).json()["meta"], {})
        response = self.client.patch(path, json={"entry_type": "BOOK", "meta": {"authors": [" Author "]}})
        self.assertEqual(response.status_code, 200, response.text)
        self.assertEqual(response.json()["meta"], {"authors": ["Author"]})
        before = self.client.get(path).json()
        self.assertEqual(self.client.post(path + "/logs", json={}).status_code, 422)
        self.assertEqual(self.client.get(path).json()["log_count"], before["log_count"])
        with Session(self.engine) as session:
            before_count = len(session.scalars(select(ListEntry)).all())
        self.assertEqual(self.create(meta={"rating": 5}).status_code, 422)
        with Session(self.engine) as session:
            self.assertEqual(len(session.scalars(select(ListEntry)).all()), before_count)

    def test_update_log_preserves_omitted_fields_and_count(self):
        entry = self.create(log={"note": "First watch", "rating": 8.9, "occurred_at": "2026-09-30T18:00:00Z"}).json()
        log = entry["logs"][0]
        entry_path = f"/lists/1/entries/{entry['id']}"
        path = f"{entry_path}/logs/{log['id']}"
        response = self.client.patch(path, json={"rating": 9.1})
        self.assertEqual(response.status_code, 200, response.text)
        updated = response.json()
        self.assertEqual(updated["rating"], 9.1)
        self.assertEqual(updated["note"], log["note"])
        self.assertEqual(updated["occurred_at"], log["occurred_at"])
        self.assertEqual(updated["created_at"], log["created_at"])
        self.assertEqual(updated["id"], log["id"])
        self.assertEqual(self.client.get(entry_path).json()["log_count"], 1)
        response = self.client.patch(path, json={"rating": None, "occurred_at": None, "note": " Revised note "})
        self.assertEqual(response.status_code, 200, response.text)
        self.assertEqual(response.json()["note"], "Revised note")
        self.assertIsNone(response.json()["rating"])
        self.assertIsNone(response.json()["occurred_at"])
        persisted = self.client.get(entry_path).json()["logs"][0]
        self.assertEqual(persisted["note"], "Revised note")
        self.assertIsNone(persisted["rating"])

    def test_invalid_log_updates_leave_log_unchanged(self):
        entry = self.create().json()
        entry_path = f"/lists/1/entries/{entry['id']}"
        path = f"{entry_path}/logs/{entry['logs'][0]['id']}"
        original = self.client.get(entry_path).json()
        for body in ({}, {"rating": None}, {"note": " "}, {"rating": 8.95}, {"rating": 11}, {"rating": True}, {"entry_id": 123}, {"occurred_at": "2026-09-30T18:00:00"}):
            with self.subTest(body=body):
                response = self.client.patch(path, json=body)
                self.assertEqual(response.status_code, 422, response.text)
                self.assertEqual(self.client.get(entry_path).json(), original)

    def test_update_log_enforces_ownership_and_parent_scope(self):
        entry = self.create().json()
        other = self.create().json()
        log_id = entry["logs"][0]["id"]
        for list_id, entry_id, target_log in (
            (2, entry["id"], log_id), (3, entry["id"], log_id),
            (1, other["id"], log_id), (1, entry["id"], 999),
        ):
            response = self.client.patch(f"/lists/{list_id}/entries/{entry_id}/logs/{target_log}", json={"rating": 5})
            self.assertEqual(response.status_code, 404)
        self.assertEqual(self.client.get(f"/lists/1/entries/{entry['id']}").json()["logs"][0]["rating"], 8.9)

    def test_update_log_can_retain_only_existing_media(self):
        entry = self.create().json()
        log_id = entry["logs"][0]["id"]
        with Session(self.engine) as session:
            session.add(EntryMedia(log_id=log_id, url="https://example.com/photo.jpg", media_type="image"))
            session.commit()
        path = f"/lists/1/entries/{entry['id']}/logs/{log_id}"
        response = self.client.patch(path, json={"rating": None})
        self.assertEqual(response.status_code, 200, response.text)
        self.assertIsNone(response.json()["rating"])
        self.assertEqual(len(response.json()["media"]), 1)

    def test_stale_entry_metadata_is_validated_against_current_type(self):
        entry = self.create().json()
        user = User(id=self.user_id, email="owner@example.com")

        async def interleave_updates():
            with Session(self.engine, expire_on_commit=False) as first_session:
                with Session(self.engine, expire_on_commit=False) as second_session:
                    first_db = AsyncTestSession(first_session)
                    second_db = AsyncTestSession(second_session)
                    stale = await get_owned(first_db, user, 1, entry["id"])
                    self.assertEqual(stale.entry_type, "MOVIE")
                    await update(
                        second_db, user, 1, entry["id"],
                        ListEntryUpdate(entry_type="BOOK", meta={"authors": ["Author"]}),
                    )
                    with self.assertRaises(RequestValidationError):
                        await update(
                            first_db, user, 1, entry["id"],
                            ListEntryUpdate(meta={"directors": ["Director"]}),
                        )

        asyncio.run(interleave_updates())
        stored = self.client.get(f"/lists/1/entries/{entry['id']}").json()
        self.assertEqual(stored["entry_type"], "BOOK")
        self.assertEqual(stored["meta"], {"authors": ["Author"]})

    def test_position_bounds_and_append_overflow(self):
        entry = self.create().json()
        path = f"/lists/1/entries/{entry['id']}"
        for position in (-2_147_483_649, 2_147_483_648):
            self.assertEqual(self.create(position=position).status_code, 422)
            response = self.client.patch(path, json={"position": position})
            self.assertEqual(response.status_code, 422)
            self.assertEqual(response.json()["detail"][0]["loc"], ["body", "position"])
        for position in (-2_147_483_648, 2_147_483_647):
            self.assertEqual(self.client.patch(path, json={"position": position}).status_code, 200)
        self.assertEqual(self.create().status_code, 409)

    def test_nonfinite_values_return_json_validation_errors(self):
        entry = self.create().json()
        path = f"/lists/1/entries/{entry['id']}"
        log_path = f"{path}/logs/{entry['logs'][0]['id']}"
        requests = [
            ("POST", "/lists/1/entries", {"entry_type": "CUSTOM", "title": "Film", "log": {"rating": 5}, "meta": {"nested": [float("nan")]}}),
            ("PATCH", path, {"meta": {"release_year": float("inf")}}),
            ("PATCH", path, {"title": "Changed", "meta": {"bad": float("nan")}}),
            ("POST", path + "/logs", {"rating": float("nan")}),
            ("PATCH", log_path, {"rating": float("inf")}),
        ]
        before = self.client.get(path).json()
        for method, url, body in requests:
            with self.subTest(method=method, url=url, body=body):
                response = self.client.request(
                    method, url, content=json.dumps(body),
                    headers={"content-type": "application/json"},
                )
                self.assertEqual(response.status_code, 422, response.text)
                self.assertIn("detail", response.json())
                self.assertEqual(self.client.get(path).json(), before)
        # This is valid JSON syntax, but Python parses the overflowing number as infinity.
        response = self.client.patch(
            log_path, content='{"rating": 1e400}',
            headers={"content-type": "application/json"},
        )
        self.assertEqual(response.status_code, 422, response.text)

    def test_null_stored_metadata_returns_object(self):
        entry = self.create().json()
        with Session(self.engine) as session:
            stored = session.get(ListEntry, entry["id"])
            stored.meta = None
            session.commit()
        self.assertEqual(self.client.get(f"/lists/1/entries/{entry['id']}").json()["meta"], {})


class ConstraintErrorTests(unittest.IsolatedAsyncioTestCase):
    async def test_duplicate_during_explicit_update_returns_409(self):
        original = Exception("duplicate")
        original.constraint_name = "ux_list_entries_list_external"
        db = AsyncMock()
        entry = ListEntry(id=1, entry_type="MOVIE", title="Film", meta={})
        result = Mock()
        result.scalar_one_or_none.return_value = entry
        db.execute.side_effect = [result, IntegrityError("update", {}, original)]
        payload = ListEntryUpdate(external_source="tmdb", external_id="603")
        with self.assertRaises(HTTPException) as raised:
            await update(db, User(id=uuid.uuid4()), 1, entry.id, payload)
        self.assertEqual(raised.exception.status_code, 409)
        db.rollback.assert_awaited_once()
        db.commit.assert_not_awaited()

    async def test_named_duplicate_returns_409_and_rolls_back(self):
        original = Exception("duplicate")
        original.constraint_name = "ux_list_entries_list_external"
        db = AsyncMock()
        db.commit.side_effect = IntegrityError("insert", {}, original)
        with self.assertRaises(HTTPException) as raised:
            await _commit(db)
        self.assertEqual(raised.exception.status_code, 409)
        db.rollback.assert_awaited_once()

    async def test_unrelated_integrity_error_is_not_hidden(self):
        db = AsyncMock()
        db.commit.side_effect = IntegrityError("insert", {}, Exception("unrelated"))
        with self.assertRaises(IntegrityError):
            await _commit(db)
        db.rollback.assert_awaited_once()


if __name__ == "__main__":
    unittest.main()
