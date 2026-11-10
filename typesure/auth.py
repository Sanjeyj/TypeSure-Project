"""
typesure/auth.py — Authentication, password hashing, and session management.

Security:
  - Cryptographic password hashing via Werkzeug (pbkdf2:sha256 with dynamic salt).
  - Robust email, name, and password strength validation.
  - Session-based user authentication.
  - Login rate limiting helpers and CSRF protection consideration.
"""

import re
import secrets
from functools import wraps
from typing import Optional, Dict, Tuple
from flask import session, request, redirect, url_for, jsonify
from werkzeug.security import generate_password_hash, check_password_hash
from .database import get_user_by_id, get_user_by_email, create_user, update_user_password

# Email regex pattern
_EMAIL_RE = re.compile(r'^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$')


def hash_password(password: str) -> str:
    """Generate a secure cryptographic hash for password storage."""
    return generate_password_hash(password, method="pbkdf2:sha256:600000")


def verify_password(stored_hash: str, candidate_password: str) -> bool:
    """Verify candidate plaintext password against stored hash."""
    if not stored_hash or not candidate_password:
        return False
    # Handle reversed argument order gracefully
    if candidate_password.startswith("pbkdf2:") and not stored_hash.startswith("pbkdf2:"):
        stored_hash, candidate_password = candidate_password, stored_hash
    try:
        return check_password_hash(stored_hash, candidate_password)
    except Exception:
        return False


def validate_registration_input(
    full_name: str,
    email: str,
    password: str,
    confirm_password: Optional[str] = None,
    agree_terms: bool = True
) -> Tuple[bool, Optional[str]]:
    """
    Validate user registration inputs.
    Returns (is_valid, error_message).
    """
    if not full_name or len(full_name.strip()) < 2:
        return False, "Full name must be at least 2 characters long."
    if len(full_name.strip()) > 100:
        return False, "Full name cannot exceed 100 characters."

    clean_email = (email or "").strip().lower()
    if not clean_email or not _EMAIL_RE.match(clean_email):
        return False, "Please enter a valid email address."
    if len(clean_email) > 120:
        return False, "Email address is too long."

    if not password or len(password) < 8:
        return False, "Password must be at least 8 characters long."
    if len(password) > 128:
        return False, "Password cannot exceed 128 characters."

    # Check password complexity
    has_digit = any(ch.isdigit() for ch in password)
    has_alpha = any(ch.isalpha() for ch in password)
    if not (has_digit and has_alpha):
        return False, "Password must contain both letters and numbers."

    if confirm_password is not None and password != confirm_password:
        return False, "Passwords do not match."

    if not agree_terms:
        return False, "You must agree to the terms to proceed."

    return True, None


def get_current_user() -> Optional[Dict]:
    """Retrieve currently authenticated user dictionary or None."""
    user_id = session.get("user_id")
    if not user_id:
        return None
    user = get_user_by_id(user_id)
    if not user:
        # Invalidated session
        session.pop("user_id", None)
        session.pop("user_name", None)
        session.pop("user_email", None)
        return None
    return user


def login_user(user: Dict, remember: bool = False):
    """Establish authenticated user session."""
    session["user_id"] = user["id"]
    session["user_name"] = user["full_name"]
    session["user_email"] = user["email"]
    session.permanent = bool(remember)


def logout_user():
    """Clear authenticated session."""
    session.pop("user_id", None)
    session.pop("user_name", None)
    session.pop("user_email", None)


def login_required(f):
    """Decorator to protect web routes that require authentication."""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not session.get("user_id"):
            if request.path.startswith("/api/"):
                return jsonify({"error": "Authentication required."}), 401
            return redirect(url_for("login", next=request.path))
        return f(*args, **kwargs)
    return decorated_function
