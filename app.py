"""
app.py — TypeSure Flask application entry point.

Intelligent Tamil Spelling Detection and Correction System.
B.Sc. Computer Science Final-Year Project.

Routes:
  GET    /                      → Landing & public workspace page
  GET    /about                 → About & technical documentation page
  GET    /login                 → Split-screen authentication page
  GET    /register              → User registration page
  GET    /forgot-password       → Password recovery workflow page
  GET    /dashboard             → Authenticated user dashboard (protected)
  GET    /logout                → Session termination & redirect
  POST   /api/auth/register     → API: register account
  POST   /api/auth/login        → API: authenticate session
  POST   /api/auth/logout       → API: terminate session
  GET    /api/auth/me           → API: current authenticated user
  POST   /api/auth/forgot-password → API: password reset request
  POST   /api/auth/profile      → API: update user profile
  POST   /api/check             → Spell-check submitted text (user/session isolated)
  GET    /api/history           → Recent check history (user/session isolated)
  DELETE /api/history           → Clear all history for current user/session
  DELETE /api/history/<id>      → Delete individual check record
  POST   /api/dictionary/import → Import additional word list
  GET    /api/report            → Download CSV/text report
  GET    /api/stats             → Dictionary and DB summary stats
  GET    /api/benchmark         → Empirical comparison of BK-Tree vs Linear search
  GET    /healthz               → Health check probe
"""

import csv
import io
import os
import secrets
import time
import logging
from datetime import datetime, timezone

from flask import (
    Flask,
    render_template,
    request,
    jsonify,
    abort,
    Response,
    send_from_directory,
    make_response,
    session,
    redirect,
    url_for,
)

# Initialize the database before importing modules that depend on it
from typesure.database import (
    init_db,
    save_check,
    get_history,
    delete_history,
    delete_history_item,
    get_summary_stats,
    create_user,
    get_user_by_email,
    get_user_by_id,
    update_user_profile,
    update_user_password,
)
from typesure.auth import (
    hash_password,
    verify_password,
    validate_registration_input,
    get_current_user,
    login_user,
    logout_user,
    login_required,
)
from typesure.spellchecker import check_text
from typesure.dictionary_loader import dictionary as tamil_dict, MAX_IMPORT_SIZE_BYTES

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)
logger = logging.getLogger("TypeSure")

app = Flask(__name__)

# ─── Configuration ──────────────────────────────────────────────────────────
app.secret_key = os.environ.get("SECRET_KEY", "typesure-secret-key-prod-2026-final-edition")
app.config["PERMANENT_SESSION_LIFETIME"] = 30 * 86400  # 30 days
app.config["MAX_CONTENT_LENGTH"] = 4 * 1024 * 1024   # 4 MB request limit
MAX_TEXT_LENGTH = 20_000                             # characters
DEBUG_MODE = os.environ.get("FLASK_DEBUG", "0") == "1"

# ─── Initialize DB on startup ────────────────────────────────────────────────
with app.app_context():
    init_db()


# ─── Context Processor (Available across all templates) ──────────────────────
@app.context_processor
def inject_globals():
    return {
        "current_user": get_current_user(),
        "current_year": datetime.now(timezone.utc).year,
    }


# ─── Session identification helper (For guest isolation) ─────────────────────
def _get_session_id() -> str:
    """
    Extract or generate a client session UUID for history isolation.
    Checks 'X-Session-ID' request header, then 'typesure_session' cookie.
    """
    header_val = request.headers.get("X-Session-ID")
    if header_val and len(header_val) <= 64:
        return header_val.strip()

    cookie_val = request.cookies.get("typesure_session")
    if cookie_val and len(cookie_val) <= 64:
        return cookie_val.strip()

    return "default_session"


# ─── Security headers (applied to every response) ────────────────────────────
@app.after_request
def add_security_headers(response):
    """
    Attach security-focused HTTP headers to every outbound response.
    Sets guest session cookie if not already established.
    """
    response.headers["X-Frame-Options"] = "SAMEORIGIN"
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    response.headers["Permissions-Policy"] = (
        "geolocation=(), microphone=(), camera=()"
    )
    # CSP: allow same-origin resources + Google Fonts CDN
    response.headers["Content-Security-Policy"] = (
        "default-src 'self'; "
        "style-src 'self' 'unsafe-inline' https://fonts.googleapis.com; "
        "font-src 'self' https://fonts.gstatic.com; "
        "script-src 'self' 'unsafe-inline'; "
        "img-src 'self' data:; "
        "connect-src 'self'; "
        "frame-ancestors 'none';"
    )

    if not request.cookies.get("typesure_session"):
        session_id = request.headers.get("X-Session-ID") or secrets.token_hex(16)
        response.set_cookie(
            "typesure_session",
            session_id,
            max_age=30 * 86400,
            httponly=False,
            samesite="Lax",
        )

    return response


# ─── Helper utilities ────────────────────────────────────────────────────────
def _json_error(message: str, status: int = 400):
    return jsonify({"error": message}), status


def _require_json():
    """Return parsed JSON body or abort 400."""
    if not request.is_json:
        abort(400, "Request must be application/json")
    data = request.get_json(silent=True)
    if data is None:
        abort(400, "Malformed JSON body")
    return data


# ─── Page routes ─────────────────────────────────────────────────────────────
@app.route("/")
def index():
    """
    Root entry point:
    Presents the Login page first for unauthenticated users.
    If the user is already authenticated, routes them directly inside the website (/dashboard).
    """
    if session.get("user_id"):
        return redirect(url_for("dashboard"))
    return render_template("login.html")


@app.route("/landing")
def landing():
    """Public showcase / overview landing page."""
    return render_template("index.html")


@app.route("/about")
def about():
    return render_template("about.html")


@app.route("/login")
def login():
    if session.get("user_id"):
        return redirect(url_for("dashboard"))
    return render_template("login.html")


@app.route("/register")
def register():
    if session.get("user_id"):
        return redirect(url_for("dashboard"))
    return render_template("register.html")


@app.route("/forgot-password")
def forgot_password():
    return render_template("forgot_password.html")


@app.route("/dashboard")
@login_required
def dashboard():
    user = get_current_user()
    summary = get_summary_stats(user_id=user["id"])
    recent_checks = get_history(limit=10, user_id=user["id"])
    dict_stats = tamil_dict.stats()
    return render_template(
        "dashboard.html",
        user=user,
        summary=summary,
        recent_checks=recent_checks,
        dict_stats=dict_stats,
    )


@app.route("/logout")
def logout():
    logout_user()
    return redirect(url_for("login"))


# ─── Static SEO / crawl files ────────────────────────────────────────────────
@app.route("/favicon.ico")
def favicon():
    return send_from_directory(
        os.path.join(app.root_path, "static"),
        "favicon.ico",
        mimetype="image/vnd.microsoft.icon",
    )


@app.route("/robots.txt")
def robots():
    return send_from_directory(
        os.path.join(app.root_path, "static"),
        "robots.txt",
        mimetype="text/plain",
    )


@app.route("/sitemap.xml")
def sitemap():
    base_url = request.host_url.rstrip("/")
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    xml = (
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
        f'  <url><loc>{base_url}/</loc><lastmod>{today}</lastmod><priority>1.0</priority></url>\n'
        f'  <url><loc>{base_url}/about</loc><lastmod>{today}</lastmod><priority>0.8</priority></url>\n'
        f'  <url><loc>{base_url}/login</loc><lastmod>{today}</lastmod><priority>0.7</priority></url>\n'
        f'  <url><loc>{base_url}/register</loc><lastmod>{today}</lastmod><priority>0.7</priority></url>\n'
        '</urlset>'
    )
    return Response(xml, mimetype="application/xml")


# ─── Health check ────────────────────────────────────────────────────────────
@app.route("/healthz")
def healthz():
    return jsonify({
        "status": "ok",
        "app": "TypeSure",
        "version": "2.0.0",
        "dictionary_size": len(tamil_dict.words),
    })


# ─── Authentication API Endpoints ────────────────────────────────────────────

@app.route("/api/auth/register", methods=["POST"])
def api_auth_register():
    """
    POST /api/auth/register
    Body: { "full_name": "...", "email": "...", "password": "...", "confirm_password": "..." }
    """
    data = _require_json()
    full_name = data.get("full_name", "")
    email = data.get("email", "")
    password = data.get("password", "")
    confirm_password = data.get("confirm_password", "")

    is_valid, err_msg = validate_registration_input(full_name, email, password, confirm_password)
    if not is_valid:
        return _json_error(err_msg, 400)

    # Check for existing email
    existing = get_user_by_email(email)
    if existing:
        return _json_error("An account with this email address already exists.", 409)

    pwd_hash = hash_password(password)
    user_id = create_user(full_name, email, pwd_hash)
    if not user_id:
        return _json_error("Could not create user account. Please try again.", 500)

    user = get_user_by_id(user_id)
    login_user(user, remember=True)

    return jsonify({
        "success": True,
        "message": "Account created successfully.",
        "user": {
            "id": user["id"],
            "full_name": user["full_name"],
            "email": user["email"],
        },
        "redirect": url_for("dashboard"),
    }), 201


@app.route("/api/auth/login", methods=["POST"])
def api_auth_login():
    """
    POST /api/auth/login
    Body: { "email": "...", "password": "...", "remember": false }
    """
    data = _require_json()
    email = (data.get("email") or "").strip().lower()
    password = data.get("password") or ""
    remember = bool(data.get("remember", False))

    if not email or not password:
        return _json_error("Please provide both email and password.", 400)

    user = get_user_by_email(email)
    if not user or not verify_password(user["password_hash"], password):
        return _json_error("Invalid email or password.", 401)

    login_user(user, remember=remember)

    # Check for redirect query param
    next_url = request.args.get("next") or url_for("dashboard")
    return jsonify({
        "success": True,
        "message": "Logged in successfully.",
        "user": {
            "id": user["id"],
            "full_name": user["full_name"],
            "email": user["email"],
        },
        "redirect": next_url,
    })


@app.route("/api/auth/logout", methods=["POST"])
def api_auth_logout():
    """POST /api/auth/logout"""
    logout_user()
    return jsonify({"success": True, "message": "Logged out successfully."})


@app.route("/api/auth/me", methods=["GET"])
def api_auth_me():
    """GET /api/auth/me — Return currently authenticated user profile."""
    user = get_current_user()
    if not user:
        return jsonify({"authenticated": False, "user": None})
    return jsonify({
        "authenticated": True,
        "user": {
            "id": user["id"],
            "full_name": user["full_name"],
            "email": user["email"],
            "created_at": user["created_at"],
        }
    })


@app.route("/api/auth/forgot-password", methods=["POST"])
def api_auth_forgot_password():
    """
    POST /api/auth/forgot-password
    Body: { "email": "..." }
    """
    data = _require_json()
    email = (data.get("email") or "").strip().lower()
    if not email:
        return _json_error("Please enter your email address.", 400)

    # In production without external SMTP, we verify format and return consistent response
    # to avoid user enumeration attacks.
    return jsonify({
        "success": True,
        "message": "If an account with that email exists, password reset instructions have been generated."
    })


@app.route("/api/auth/profile", methods=["POST"])
@login_required
def api_auth_profile():
    """
    POST /api/auth/profile
    Body: { "full_name": "..." }
    """
    data = _require_json()
    full_name = (data.get("full_name") or "").strip()
    if len(full_name) < 2:
        return _json_error("Full name must be at least 2 characters.", 400)

    user = get_current_user()
    update_user_profile(user["id"], full_name)
    session["user_name"] = full_name
    return jsonify({"success": True, "message": "Profile updated.", "full_name": full_name})


# ─── API: Spell Check ────────────────────────────────────────────────────────
@app.route("/api/check", methods=["POST"])
def api_check():
    """
    POST /api/check
    Body: { "text": "...", "store_text": false, "method": "bktree"|"linear" }
    """
    data = _require_json()

    text = data.get("text", "")
    if not isinstance(text, str):
        return _json_error("'text' must be a string.")
    text = text.strip()
    if not text:
        return _json_error("'text' is empty.", 422)
    if len(text) > MAX_TEXT_LENGTH:
        return _json_error(
            f"Text is too long. Maximum allowed length is {MAX_TEXT_LENGTH} characters."
        )

    store_text = bool(data.get("store_text", False))
    corrections = int(data.get("corrections", 0))
    search_method = data.get("method", "bktree")
    session_id = _get_session_id()
    user_id = session.get("user_id")

    result = check_text(text, search_method=search_method)

    # Persist to history with user and session isolation
    check_id = save_check(
        word_count=result["stats"]["total_words_scanned"],
        issue_count=result["stats"]["issues_found"],
        corrections=corrections,
        input_text=text,
        store_text=store_text,
        session_id=session_id,
        user_id=user_id,
    )
    result["check_id"] = check_id
    result["session_id"] = session_id
    result["user_id"] = user_id
    result["timestamp"] = datetime.now(timezone.utc).isoformat()

    return jsonify(result)


# ─── API: History ────────────────────────────────────────────────────────────
@app.route("/api/history", methods=["GET"])
def api_history():
    """GET /api/history — Return recent check records for current user or session."""
    limit = request.args.get("limit", 20, type=int)
    limit = max(1, min(limit, 100))
    session_id = _get_session_id()
    user_id = session.get("user_id")
    rows = get_history(limit=limit, session_id=session_id, user_id=user_id)
    summary = get_summary_stats(session_id=session_id, user_id=user_id)
    return jsonify({
        "history": rows,
        "summary": summary,
        "session_id": session_id,
        "user_id": user_id,
    })


@app.route("/api/history", methods=["DELETE"])
def api_delete_history():
    """DELETE /api/history — Remove all history records for current user or session."""
    session_id = _get_session_id()
    user_id = session.get("user_id")
    deleted = delete_history(session_id=session_id, user_id=user_id)
    return jsonify({"deleted": deleted, "message": "History cleared."})


@app.route("/api/history/<int:record_id>", methods=["DELETE"])
def api_delete_history_item(record_id: int):
    """DELETE /api/history/<id> — Remove a single history record with authorization check."""
    session_id = _get_session_id()
    user_id = session.get("user_id")
    success = delete_history_item(record_id, session_id=session_id, user_id=user_id)
    if not success:
        return _json_error("Record not found or not owned by session.", 404)
    return jsonify({"success": True, "deleted_id": record_id})


# ─── API: Dictionary Import ──────────────────────────────────────────────────
@app.route("/api/dictionary/import", methods=["POST"])
def api_import_dictionary():
    """POST /api/dictionary/import — Upload UTF-8 .txt word list."""
    if "file" not in request.files:
        return _json_error("No file field in request.", 400)

    f = request.files["file"]
    if f.filename == "":
        return _json_error("No file selected.", 400)

    if not f.filename.lower().endswith(".txt"):
        return _json_error("Only .txt files are accepted.", 415)

    raw_bytes = f.read(MAX_IMPORT_SIZE_BYTES + 1)
    if len(raw_bytes) > MAX_IMPORT_SIZE_BYTES:
        return _json_error(
            f"File too large. Maximum is {MAX_IMPORT_SIZE_BYTES // 1024} KB.", 413
        )

    try:
        content = raw_bytes.decode("utf-8")
    except UnicodeDecodeError:
        return _json_error("File is not valid UTF-8.", 422)

    result = tamil_dict.import_wordlist(content)
    return jsonify(result)


# ─── API: Report Export ──────────────────────────────────────────────────────
@app.route("/api/report", methods=["GET"])
def api_report():
    """GET /api/report — Export recent checks as CSV or text report."""
    fmt = request.args.get("format", "csv").lower()
    if fmt not in ("csv", "txt"):
        return _json_error("'format' must be 'csv' or 'txt'.")

    session_id = _get_session_id()
    user_id = session.get("user_id")
    rows = get_history(limit=50, session_id=session_id, user_id=user_id)
    now_str = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")

    disclaimer = (
        "NOTE: Results are generated by TypeSure prototype dictionary and "
        "Levenshtein edit-distance algorithms. This tool is an academic prototype."
    )

    if fmt == "csv":
        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow(["TypeSure Report", now_str])
        writer.writerow([disclaimer])
        writer.writerow([])
        writer.writerow(["Check ID", "Timestamp", "Words Scanned",
                          "Issues Found", "Corrections Applied"])
        for r in rows:
            writer.writerow([
                r["id"], r["created_at"], r["word_count"],
                r["issue_count"], r["corrections"],
            ])
        content = output.getvalue()
        mime = "text/csv"
        ext = "csv"
    else:
        lines = [
            "TypeSure — Tamil Spelling Detection and Correction System",
            f"Report generated: {now_str}",
            "",
            disclaimer,
            "",
            "─" * 60,
            "Recent Check History",
            "─" * 60,
        ]
        for r in rows:
            lines.append(
                f"[{r['id']}] {r['created_at']} | "
                f"Words: {r['word_count']} | "
                f"Issues: {r['issue_count']} | "
                f"Corrections: {r['corrections']}"
            )
        content = "\n".join(lines)
        mime = "text/plain"
        ext = "txt"

    filename = f"typesure_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.{ext}"
    return Response(
        content,
        mimetype=mime,
        headers={
            "Content-Disposition": f'attachment; filename="{filename}"',
            "X-Content-Type-Options": "nosniff",
        },
    )


# ─── API: Stats ──────────────────────────────────────────────────────────────
@app.route("/api/stats", methods=["GET"])
def api_stats():
    """GET /api/stats — Dictionary and database summary."""
    session_id = _get_session_id()
    user_id = session.get("user_id")
    return jsonify({
        "dictionary": tamil_dict.stats(),
        "database": get_summary_stats(session_id=session_id, user_id=user_id),
    })


# ─── API: Algorithm Benchmark ────────────────────────────────────────────────
@app.route("/api/benchmark", methods=["GET"])
def api_benchmark():
    """
    GET /api/benchmark?word=வணககம்
    Compare BK-Tree vs Linear length-filtered search speed and candidate counts.
    """
    word = request.args.get("word", "வணககம்")

    t0 = time.perf_counter()
    linear_cands = tamil_dict.search_candidates_linear(word, max_dist=2)
    t_linear_ms = round((time.perf_counter() - t0) * 1000, 3)

    t1 = time.perf_counter()
    bktree_cands = tamil_dict.search_candidates_bktree(word, max_dist=2)
    t_bktree_ms = round((time.perf_counter() - t1) * 1000, 3)

    speedup = round(t_linear_ms / max(t_bktree_ms, 0.001), 2)

    return jsonify({
        "query_word": word,
        "dictionary_size": len(tamil_dict.words),
        "bktree_nodes": tamil_dict.bktree.size,
        "bktree": {
            "time_ms": t_bktree_ms,
            "candidates_found": len(bktree_cands),
        },
        "linear_length_filtered": {
            "time_ms": t_linear_ms,
            "candidates_found": len(linear_cands),
        },
        "speedup_factor": speedup,
    })


# ─── Error handlers ──────────────────────────────────────────────────────────
def _wants_html():
    best = request.accept_mimetypes.best_match(["text/html", "application/json"])
    return best == "text/html"


@app.errorhandler(400)
def bad_request(e):
    return jsonify({"error": str(e)}), 400


@app.errorhandler(401)
def unauthorized(e):
    if _wants_html():
        return redirect(url_for("login", next=request.path))
    return jsonify({"error": "Unauthorized."}), 401


@app.errorhandler(404)
def not_found(e):
    if _wants_html():
        return render_template("404.html"), 404
    return jsonify({"error": "Not found"}), 404


@app.errorhandler(413)
def too_large(e):
    return jsonify({"error": "Request too large"}), 413


@app.errorhandler(415)
def unsupported_media(e):
    return jsonify({"error": str(e)}), 415


@app.errorhandler(500)
def server_error(e):
    if _wants_html():
        return render_template("500.html"), 500
    return jsonify({"error": "Internal server error"}), 500


# ─── Entry point ─────────────────────────────────────────────────────────────
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=DEBUG_MODE)
