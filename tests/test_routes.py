"""
test_routes.py — Integration tests for the Flask API routes.
"""

import sys
import os
import json
import io

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import pytest
from app import app
from typesure.database import init_db


@pytest.fixture
def client():
    app.config["TESTING"] = True
    # Use in-memory SQLite for tests? No — the DB module uses a file.
    # We just initialize normally; tests will write to the real data/typesure.db.
    with app.test_client() as client:
        with app.app_context():
            init_db()
        yield client


# ──────────────────────────────────────────────────────────────────────────────
# Homepage
# ──────────────────────────────────────────────────────────────────────────────

class TestHomepage:
    def test_homepage_loads(self, client):
        r = client.get("/")
        assert r.status_code == 200
        assert b"TypeSure" in r.data

    def test_about_page_loads(self, client):
        r = client.get("/about")
        assert r.status_code == 200
        assert b"About" in r.data

    def test_404(self, client):
        r = client.get("/nonexistent-path-xyz")
        assert r.status_code == 404


# ──────────────────────────────────────────────────────────────────────────────
# /api/check
# ──────────────────────────────────────────────────────────────────────────────

class TestApiCheck:
    def _post(self, client, body):
        return client.post(
            "/api/check",
            data=json.dumps(body),
            content_type="application/json",
        )

    def test_valid_tamil_text(self, client):
        r = self._post(client, {"text": "வணக்கம் நன்றி"})
        assert r.status_code == 200
        data = r.get_json()
        assert "stats" in data
        assert "issues" in data
        assert "spans" in data

    def test_empty_text_returns_422(self, client):
        r = self._post(client, {"text": ""})
        assert r.status_code == 422

    def test_whitespace_only_returns_422(self, client):
        r = self._post(client, {"text": "   "})
        assert r.status_code == 422

    def test_non_json_returns_400(self, client):
        r = client.post("/api/check", data="plain text", content_type="text/plain")
        assert r.status_code == 400

    def test_malformed_json(self, client):
        r = client.post("/api/check", data="{bad json", content_type="application/json")
        assert r.status_code == 400

    def test_text_too_long(self, client):
        r = self._post(client, {"text": "வ" * 21000})
        assert r.status_code == 400

    def test_missing_text_field(self, client):
        r = self._post(client, {"not_text": "hello"})
        # 'text' defaults to empty string → 422
        assert r.status_code == 422

    def test_mixed_text(self, client):
        r = self._post(client, {"text": "Hello வணக்கம் world"})
        data = r.get_json()
        flagged = [i["word"] for i in data["issues"]]
        assert "Hello" not in flagged
        assert "world" not in flagged

    def test_response_has_check_id(self, client):
        r = self._post(client, {"text": "வணக்கம்"})
        data = r.get_json()
        assert "check_id" in data
        assert isinstance(data["check_id"], int)

    def test_known_word_not_flagged(self, client):
        r = self._post(client, {"text": "வணக்கம்"})
        data = r.get_json()
        flagged = [i["word"] for i in data["issues"]]
        assert "வணக்கம்" not in flagged

    def test_stats_in_range(self, client):
        r = self._post(client, {"text": "வணக்கம் நன்றி"})
        stats = r.get_json()["stats"]
        assert stats["total_words_scanned"] >= 0
        assert 0 <= stats["dictionary_coverage_pct"] <= 100


# ──────────────────────────────────────────────────────────────────────────────
# /api/history
# ──────────────────────────────────────────────────────────────────────────────

class TestApiHistory:
    def test_get_history(self, client):
        r = client.get("/api/history")
        assert r.status_code == 200
        data = r.get_json()
        assert "history" in data
        assert isinstance(data["history"], list)

    def test_delete_history(self, client):
        r = client.delete("/api/history")
        assert r.status_code == 200
        data = r.get_json()
        assert "deleted" in data

    def test_history_after_check(self, client):
        client.post(
            "/api/check",
            data=json.dumps({"text": "வணக்கம்"}),
            content_type="application/json",
        )
        r = client.get("/api/history")
        data = r.get_json()
        assert len(data["history"]) >= 1


# ──────────────────────────────────────────────────────────────────────────────
# /api/dictionary/import
# ──────────────────────────────────────────────────────────────────────────────

class TestApiDictionaryImport:
    def _upload(self, client, content, filename="test.txt", content_type="text/plain"):
        data = {"file": (io.BytesIO(content), filename)}
        return client.post(
            "/api/dictionary/import",
            data=data,
            content_type="multipart/form-data",
        )

    def test_valid_import(self, client):
        content = "வணக்கம்\nநன்றி\n".encode("utf-8")
        r = self._upload(client, content)
        assert r.status_code == 200
        data = r.get_json()
        assert "added" in data

    def test_non_txt_rejected(self, client):
        r = self._upload(client, b"hello", filename="words.csv")
        assert r.status_code == 415

    def test_no_file_field(self, client):
        r = client.post("/api/dictionary/import", data={}, content_type="multipart/form-data")
        assert r.status_code == 400

    def test_non_utf8_rejected(self, client):
        r = self._upload(client, b"\xff\xfe bad bytes")
        assert r.status_code == 422

    def test_non_tamil_words_skipped(self, client):
        content = b"hello\nworld\n"
        r = self._upload(client, content)
        data = r.get_json()
        assert data["invalid"] == 2


# ──────────────────────────────────────────────────────────────────────────────
# /api/report
# ──────────────────────────────────────────────────────────────────────────────

class TestApiReport:
    def test_csv_report(self, client):
        r = client.get("/api/report?format=csv")
        assert r.status_code == 200
        assert "text/csv" in r.content_type
        assert b"TypeSure" in r.data

    def test_txt_report(self, client):
        r = client.get("/api/report?format=txt")
        assert r.status_code == 200
        assert b"TypeSure" in r.data

    def test_invalid_format(self, client):
        r = client.get("/api/report?format=pdf")
        assert r.status_code == 400

    def test_report_has_disclaimer(self, client):
        r = client.get("/api/report?format=txt")
        assert b"prototype" in r.data.lower()


# ──────────────────────────────────────────────────────────────────────────────
# /api/stats
# ──────────────────────────────────────────────────────────────────────────────

class TestApiStats:
    def test_stats_structure(self, client):
        r = client.get("/api/stats")
        assert r.status_code == 200
        data = r.get_json()
        assert "dictionary" in data
        assert "database" in data
        assert "total_words" in data["dictionary"]
