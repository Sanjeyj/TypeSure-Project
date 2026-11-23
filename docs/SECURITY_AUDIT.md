# TypeSure — Application Security Audit & Hardening Report

**Audit Standards Aligned**: OWASP ASVS v4.0 / OWASP Top 10  
**Scope**: Backend API, Authentication Architecture, Authorization & Data Isolation, Frontend DOM Safety  
**Classification**: Academic & Production-Grade Web Application  

---

## 1. Threat Modeling & Security Architecture

TypeSure operates as a privacy-centric Tamil language processing platform. Because users may submit sensitive personal, legal, or literary text, the architecture enforces a strict zero-leakage, local-processing-first design.

```text
[ Browser Client ]
       │
       ▼ (HTTPS / TLS 1.3)
[ Vercel Edge / Reverse Proxy ]
       │  - Strict-Transport-Security: max-age=63072000
       │  - Content-Security-Policy (Restricted Origins)
       │  - Frame-Options: SAMEORIGIN
       ▼
[ Flask Application Layer ]
       ├── Rate Limiter (Sliding Window per IP -> HTTP 429)
       ├── Session Guard (@login_required / HttpOnly SameSite=Lax Cookie)
       ├── Content-Length Guard (Max 4 MB Payload)
       └── Input Validator & Unicode Normalizer
              │
              ▼
[ SQLite Isolated Storage ]
       ├── Parameterized SQL Queries (Zero Raw SQL Concatenation)
       └── Per-User Logical Data Partitioning (WHERE user_id = ?)
```

---

## 2. OWASP Top 10 Compliance Matrix

| Vulnerability Category | Risk Level | Implemented Mitigation Mechanism | Verification Status |
|---|---|---|---|
| **A01: Broken Access Control** | High | Server-side `@login_required` route guard; strict `user_id` filtering on all check, history, and delete endpoints. Unauthenticated attempts redirect to `/login` or return `401`. | **Verified via Automated Tests** |
| **A02: Cryptographic Failures** | High | Passwords hashed using PBKDF2 with SHA-256 and dynamic cryptographic salt (600,000 rounds). Session secrets generated via `secrets.token_hex(32)`. Zero plaintext credential storage. | **Verified via Automated Tests** |
| **A03: Injection (SQL / Command)** | Critical | 100% of SQLite database interactions use parameterized queries (`?` placeholders). No user input is ever passed to `exec`, `eval`, or shell commands. | **Verified via Code Review & Tests** |
| **A04: Insecure Design** | Medium | User isolation built directly into database schema; rate limiting on authentication routes prevents brute-force credential stuffing. | **Verified via Automated Tests** |
| **A05: Security Misconfiguration** | Medium | Outbound security headers attached to every response: `X-Content-Type-Options: nosniff`, `X-Frame-Options: SAMEORIGIN`, `Referrer-Policy: strict-origin-when-cross-origin`, strict `Permissions-Policy`. | **Verified via HTTP Probing** |
| **A06: Vulnerable Dependencies** | Low | Minimal dependency footprint (`flask`, `werkzeug`, `pytest`). No obsolete or vulnerable native binary modules. | **Verified via pip check** |
| **A07: Identification & Auth Failures** | High | Strict password strength requirements (min 8 chars, mixed letters and digits); email validation regex; account enumeration prevention on password recovery. | **Verified via Automated Tests** |
| **A08: Software & Data Integrity** | Low | UTF-8 validation on dictionary file imports; max import size limit (2 MB / 50,000 words); idempotent deduplication. | **Verified via Automated Tests** |
| **A09: Security Logging & Monitoring** | Low | Python standard logging with structured formatting; sensitive passwords and auth tokens excluded from log outputs. | **Verified via Code Review** |
| **A10: Server-Side Request Forgery (SSRF)** | None | Zero external HTTP requests made by the backend during spell-checking. All dictionary and NLP models operate purely in local memory. | **Verified via Architecture** |

---

## 3. Dedicated Security Controls

### 3.1 Rate Limiting Architecture
To prevent brute-force dictionary attacks against user accounts, an in-memory sliding-window rate limiter is applied to sensitive endpoints:
- `POST /api/auth/login`: Maximum 10 requests per 60 seconds per IP.
- `POST /api/auth/register`: Maximum 10 requests per 60 seconds per IP.
- `POST /api/auth/forgot-password`: Maximum 5 requests per 60 seconds per IP.
When the threshold is reached, the server responds with `HTTP 429 Too Many Requests` including a `retry_after` timestamp.

### 3.2 Cross-Site Scripting (XSS) Prevention
1. **Zero `innerHTML` User Injection**: In `app.js` and `dashboard.js`, user-submitted text and suggestion labels are strictly manipulated via `element.textContent` or `document.createTextNode()`.
2. **Content Security Policy (CSP)**: Outbound headers enforce `default-src 'self'`. External script sources are prohibited.

### 3.3 CSRF and Session Security
- The session cookie `typesure_session` is configured with `SameSite=Lax` and lifetime limits.
- State-changing API endpoints require `Content-Type: application/json` and validate JSON structure, preventing simple form submission CSRF attacks.

---

## 4. Automated Security Verification Test Suite

Security behaviors are tested under `tests/test_auth.py` and `tests/test_security.py`:
- `test_rate_limiting_enforcement`: Asserts HTTP 429 when threshold exceeded.
- `test_unauthenticated_api_access_blocked`: Asserts HTTP 401 on protected endpoints.
- `test_sql_injection_resilience`: Submits classic SQL payloads (`' OR '1'='1`) into login and check endpoints.
- `test_xss_payload_neutralization`: Submits `<script>alert(1)</script>` into Tamil text inputs.
- `test_oversized_payload_rejected`: Verifies HTTP 413 or validation rejection when input exceeds max bounds.
