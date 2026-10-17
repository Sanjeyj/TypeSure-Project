"""
app.py — TypeSure Flask application entry point.

Routes:
  GET  /                      → Main editor page
  GET  /about                 → About / limitations page
  POST /api/check             → Spell-check submitted text
  GET  /api/history           → Recent check history
  DELETE /api/history         → Clear all history
  POST /api/dictionary/import → Import additional word list
  GET  /api/report            → Download CSV/text report
  GET  /api/stats             → Dictionary and DB summary stats
"""

import csv
import io
import os
import json
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
)

# Initialize the database before importing modules that depend on it
from typesure.database import init_db, save_check, get_history, delete_history, get_summary_stats
from typesure.spellchecker import check_text
from typesure.dictionary_loader import dictionary as tamil_dict, MAX_IMPORT_SIZE_BYTES

app = Flask(__name__)

# ─── Configuration ──────────────────────────────────────────────────────────

app.config["MAX_CONTENT_LENGTH"] = 4 * 1024 * 1024   # 4 MB request limit
MAX_TEXT_LENGTH = 20_000   # characters
DEBUG_MODE = os.environ.get("FLASK_DEBUG", "0") == "1"

# ─── Initialize DB on startup ────────────────────────────────────────────────

with app.app_context():
    init_db()


# ─── Security headers (applied to every response) ────────────────────────────

@app.after_request
def add_security_headers(response):
    """
    Attach security-focused HTTP headers to every outbound response.
    CSP is intentionally permissive for the Google Fonts CDN and local assets.
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
        "script-src 'self'; "
        "img-src 'self' data:; "
        "connect-src 'self'; "
        "frame-ancestors 'none';"
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
    return render_template("index.html")


@app.route("/about")
def about():
    return render_template("about.html")


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
    """Dynamically generate a minimal sitemap for the two public pages."""
    base_url = request.host_url.rstrip("/")
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    xml = (
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
        f'  <url><loc>{base_url}/</loc><lastmod>{today}</lastmod><priority>1.0</priority></url>\n'
        f'  <url><loc>{base_url}/about</loc><lastmod>{today}</lastmod><priority>0.8</priority></url>\n'
        '</urlset>'
    )
    return Response(xml, mimetype="application/xml")


# ─── Health check (for deployment probes) ────────────────────────────────────

@app.route("/healthz")
def healthz():
    """Lightweight health probe — returns 200 JSON when the app is up."""
    return jsonify({"status": "ok", "app": "TypeSure"})


# ─── API: Spell Check ────────────────────────────────────────────────────────

@app.route("/api/check", methods=["POST"])
def api_check():
    """
    POST /api/check
    Body: { "text": "...", "store_text": false }

    Returns spell-check results including spans, issues, and statistics.
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

    result = check_text(text)

    # Persist to history
    check_id = save_check(
        word_count=result["stats"]["total_words_scanned"],
        issue_count=result["stats"]["issues_found"],
        corrections=corrections,
        input_text=text,
        store_text=store_text,
    )
    result["check_id"] = check_id
    result["timestamp"] = datetime.now(timezone.utc).isoformat()

    return jsonify(result)


# ─── API: History ────────────────────────────────────────────────────────────

@app.route("/api/history", methods=["GET"])
def api_history():
    """GET /api/history — Return the 20 most recent check records."""
    limit = request.args.get("limit", 20, type=int)
    limit = max(1, min(limit, 100))
    rows = get_history(limit=limit)
    summary = get_summary_stats()
    return jsonify({"history": rows, "summary": summary})


@app.route("/api/history", methods=["DELETE"])
def api_delete_history():
    """DELETE /api/history — Remove all history records."""
    deleted = delete_history()
    return jsonify({"deleted": deleted, "message": "History cleared."})


# ─── API: Dictionary Import ──────────────────────────────────────────────────

@app.route("/api/dictionary/import", methods=["POST"])
def api_import_dictionary():
    """
    POST /api/dictionary/import
    Accepts a UTF-8 text file upload (multipart/form-data, field: 'file').
    """
    if "file" not in request.files:
        return _json_error("No file field in request.", 400)

    f = request.files["file"]
    if f.filename == "":
        return _json_error("No file selected.", 400)

    # Enforce .txt extension only
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
    """
    GET /api/report
    Query params:
      check_id  : optional int — if provided, include check-level data
      format    : 'csv' (default) or 'txt'

    Returns a downloadable report file.
    """
    fmt = request.args.get("format", "csv").lower()
    if fmt not in ("csv", "txt"):
        return _json_error("'format' must be 'csv' or 'txt'.")

    # Pull recent history for the report
    rows = get_history(limit=50)
    now_str = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")

    disclaimer = (
        "NOTE: Results are generated by a limited prototype dictionary and "
        "may not reflect all correct Tamil spellings. This tool is a student "
        "prototype and is NOT a production-grade Tamil spell checker."
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
    return jsonify({
        "dictionary": tamil_dict.stats(),
        "database": get_summary_stats(),
    })


# ─── Error handlers ──────────────────────────────────────────────────────────

def _wants_html():
    """Return True when the request was made by a browser expecting HTML."""
    best = request.accept_mimetypes.best_match(["text/html", "application/json"])
    return best == "text/html"


@app.errorhandler(400)
def bad_request(e):
    return jsonify({"error": str(e)}), 400


@app.errorhandler(404)
def not_found(e):
    # Return a styled HTML 404 page for browser requests; JSON for API clients
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
