"""
tests/test_auth.py
Unit and Integration tests for TypeSure Authentication and Per-User Isolation.
"""

import os
import sys
from pathlib import Path

# Ensure application root is in python module search path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import pytest
import tempfile
from typesure.auth import (
    hash_password,
    verify_password,
    validate_registration_input,
)
from typesure import database


@pytest.fixture
def temp_db(monkeypatch):
    """Provide an isolated temporary SQLite database for tests."""
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
        db_path = f.name
    
    # Safely point database module to temporary file
    monkeypatch.setattr(database, "_DB_PATH", Path(db_path))
    monkeypatch.setattr(database, "_DB_DIR", Path(db_path).parent)
    database.init_db()
    yield db_path
    try:
        os.remove(db_path)
    except OSError:
        pass


@pytest.fixture
def app_client(temp_db):
    """Provide Flask test client with isolated database."""
    from app import app
    app.config["TESTING"] = True
    app.config["WTF_CSRF_ENABLED"] = False
    with app.test_client() as client:
        yield client


class TestPasswordSecurity:
    """Test PBKDF2 cryptographic hashing and verification."""

    def test_hash_format(self):
        h = hash_password("Secret123!")
        assert h.startswith("pbkdf2:sha256:")
        assert len(h) > 50

    def test_verify_correct_password(self):
        h = hash_password("ValidPassword2026")
        assert verify_password(h, "ValidPassword2026") is True
        # Also handles reversed argument order gracefully
        assert verify_password("ValidPassword2026", h) is True

    def test_verify_wrong_password(self):
        h = hash_password("ValidPassword2026")
        assert verify_password(h, "WrongPassword!") is False

    def test_empty_password_verify(self):
        h = hash_password("ValidPassword2026")
        assert verify_password(h, "") is False
        assert verify_password("", h) is False


class TestInputValidation:
    """Test registration input validation rules."""

    def test_valid_input(self):
        is_valid, err = validate_registration_input(
            "Dr. Raman", "raman@example.com", "SecurePass123", "SecurePass123", True
        )
        assert is_valid is True
        assert err is None

    def test_missing_name(self):
        is_valid, err = validate_registration_input(
            "", "raman@example.com", "SecurePass123", "SecurePass123", True
        )
        assert is_valid is False
        assert "name" in err.lower()

    def test_invalid_email(self):
        is_valid, err = validate_registration_input(
            "Raman", "not-an-email", "SecurePass123", "SecurePass123", True
        )
        assert is_valid is False
        assert "email" in err.lower()

    def test_short_password(self):
        is_valid, err = validate_registration_input(
            "Raman", "raman@example.com", "123", "123", True
        )
        assert is_valid is False
        assert "8 characters" in err

    def test_password_mismatch(self):
        is_valid, err = validate_registration_input(
            "Raman", "raman@example.com", "SecurePass123", "Mismatch456", True
        )
        assert is_valid is False
        assert "match" in err.lower()

    def test_terms_not_accepted(self):
        is_valid, err = validate_registration_input(
            "Raman", "raman@example.com", "SecurePass123", "SecurePass123", False
        )
        assert is_valid is False
        assert "terms" in err.lower()


class TestDatabaseUserCRUD:
    """Test user database records creation, lookup, and updates."""

    def test_create_and_retrieve_user(self, temp_db):
        uid = database.create_user(
            full_name="Dr. Raman",
            email="raman@example.com",
            password_hash=hash_password("Pass1234"),
        )
        assert uid is not None

        user = database.get_user_by_email("raman@example.com")
        assert user is not None
        assert user["id"] == uid
        assert user["full_name"] == "Dr. Raman"
        assert user["email"] == "raman@example.com"

        user_by_id = database.get_user_by_id(uid)
        assert user_by_id is not None
        assert user_by_id["email"] == "raman@example.com"

    def test_duplicate_email_rejected(self, temp_db):
        database.create_user("User A", "user@example.com", "hash1")
        duplicate_id = database.create_user("User B", "user@example.com", "hash2")
        assert duplicate_id is None

    def test_update_profile(self, temp_db):
        uid = database.create_user("Old Name", "update@example.com", "hash")
        assert database.update_user_profile(uid, "New Name") is True
        user = database.get_user_by_id(uid)
        assert user["full_name"] == "New Name"

    def test_update_password(self, temp_db):
        uid = database.create_user("User", "pw@example.com", hash_password("oldPass1"))
        new_hash = hash_password("newPass123")
        assert database.update_user_password(uid, new_hash) is True
        user = database.get_user_by_id(uid)
        assert verify_password(user["password_hash"], "newPass123") is True


class TestAuthRoutesAndIsolation:
    """Test Flask authentication endpoints, sessions, and data isolation."""

    def test_register_api(self, app_client):
        res = app_client.post(
            "/api/auth/register",
            json={
                "full_name": "Tamil Scholar",
                "email": "scholar@typesure.ta",
                "password": "StrongPassword99!",
                "confirm_password": "StrongPassword99!",
                "agree_terms": True,
            },
        )
        assert res.status_code == 201
        data = res.get_json()
        assert data["success"] is True
        assert data["user"]["email"] == "scholar@typesure.ta"

    def test_register_duplicate_fails(self, app_client):
        payload = {
            "full_name": "Scholar 1",
            "email": "dup@typesure.ta",
            "password": "Password123!",
            "confirm_password": "Password123!",
            "agree_terms": True,
        }
        res1 = app_client.post("/api/auth/register", json=payload)
        assert res1.status_code == 201

        res2 = app_client.post("/api/auth/register", json=payload)
        assert res2.status_code == 409
        data = res2.get_json()
        assert "already exists" in data["error"].lower()

    def test_login_flow(self, app_client):
        # Register user
        app_client.post(
            "/api/auth/register",
            json={
                "full_name": "Auth User",
                "email": "auth@typesure.ta",
                "password": "MySecretPassword1",
                "confirm_password": "MySecretPassword1",
                "agree_terms": True,
            },
        )

        # Wrong password
        bad_res = app_client.post(
            "/api/auth/login",
            json={"email": "auth@typesure.ta", "password": "WrongPassword"},
        )
        assert bad_res.status_code == 401

        # Correct password
        good_res = app_client.post(
            "/api/auth/login",
            json={"email": "auth@typesure.ta", "password": "MySecretPassword1"},
        )
        assert good_res.status_code == 200
        assert good_res.get_json()["success"] is True

        # /api/auth/me should return current user
        me_res = app_client.get("/api/auth/me")
        assert me_res.status_code == 200
        assert me_res.get_json()["user"]["email"] == "auth@typesure.ta"

        # Logout
        logout_res = app_client.post("/api/auth/logout")
        assert logout_res.status_code == 200

        # /api/auth/me after logout
        me_res2 = app_client.get("/api/auth/me")
        assert me_res2.get_json()["user"] is None

    def test_dashboard_route_protection(self, app_client):
        # Unauthenticated access redirects to /login
        res = app_client.get("/dashboard")
        assert res.status_code == 302
        assert "/login" in res.headers["Location"]

        # Authenticate
        app_client.post(
            "/api/auth/register",
            json={
                "full_name": "Dashboard User",
                "email": "dash@typesure.ta",
                "password": "Password123!",
                "confirm_password": "Password123!",
                "agree_terms": True,
            },
        )

        # Authenticated access succeeds
        dash_res = app_client.get("/dashboard")
        assert dash_res.status_code == 200
        assert b"Dashboard Overview" in dash_res.data
        assert b"dash@typesure.ta" in dash_res.data

    def test_per_user_history_isolation(self, app_client):
        # Create User 1 and run a check
        app_client.post(
            "/api/auth/register",
            json={
                "full_name": "User One",
                "email": "one@typesure.ta",
                "password": "Password123!",
                "confirm_password": "Password123!",
                "agree_terms": True,
            },
        )
        app_client.post("/api/check", json={"text": "வணக்கம்", "store_text": True})

        # Fetch history for User 1
        h1 = app_client.get("/api/history").get_json()["history"]
        assert len(h1) == 1

        # Logout User 1
        app_client.post("/api/auth/logout")

        # Create User 2 and verify history is empty
        app_client.post(
            "/api/auth/register",
            json={
                "full_name": "User Two",
                "email": "two@typesure.ta",
                "password": "Password123!",
                "confirm_password": "Password123!",
                "agree_terms": True,
            },
        )
        h2 = app_client.get("/api/history").get_json()["history"]
        assert len(h2) == 0  # User 2 cannot see User 1's history!

    def test_root_serves_login_first_then_dashboard(self, app_client):
        # 1. Unauthenticated user visits root "/" -> gets Login page first (200 OK)
        res_guest = app_client.get("/")
        assert res_guest.status_code == 200
        assert b"Sign in to continue" in res_guest.data
        assert b"login-form" in res_guest.data

        # 2. Authenticate user
        app_client.post(
            "/api/auth/register",
            json={
                "full_name": "Root Test User",
                "email": "rootuser@typesure.ta",
                "password": "Password123!",
                "confirm_password": "Password123!",
                "agree_terms": True,
            },
        )

        # 3. Authenticated user visits root "/" -> redirected inside to /dashboard (302)
        res_auth = app_client.get("/")
        assert res_auth.status_code == 302
        assert "/dashboard" in res_auth.headers["Location"]

        # 4. Authenticated user visits /login -> redirected inside to /dashboard (302)
        res_login = app_client.get("/login")
        assert res_login.status_code == 302
        assert "/dashboard" in res_login.headers["Location"]

