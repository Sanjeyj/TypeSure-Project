# TypeSure — Production Deployment & Operations Guide

## 1. Hosting Environment Specifications

- **Live Production URL**: [https://type-sure-project.vercel.app/](https://type-sure-project.vercel.app/)
- **Repository**: [https://github.com/Sanjeyj/TypeSure-Project](https://github.com/Sanjeyj/TypeSure-Project)
- **Deployment Platform**: Vercel Serverless (Python 3.10+ runtime via WSGI adapter)
- **Database Engine**: SQLite with `/tmp` filesystem routing in serverless environments

---

## 2. Environment Variables Configuration

| Variable Name | Purpose | Example / Recommended Value |
|---|---|---|
| `SECRET_KEY` | Cryptographic session encryption key | `typesure_sec_7f9b8c2d1e0a...` |
| `VERCEL` | Auto-populated by Vercel; routes DB to `/tmp` | `1` |
| `FLASK_ENV` | Environment execution mode | `production` |
| `PYTHONUNBUFFERED` | Flushes stdout/stderr immediately | `1` |

---

## 3. Local Installation & Setup

```bash
# 1. Clone repository
git clone https://github.com/Sanjeyj/TypeSure-Project.git
cd TypeSure-Project

# 2. Create and activate virtual environment
python -m venv venv
source venv/bin/activate       # On Linux/macOS
# or: .\venv\Scripts\Activate.ps1 # On Windows

# 3. Install pinned dependencies
pip install -r requirements.txt

# 4. Compile Tamil dictionary index
python scripts/build_dictionary.py

# 5. Run automated test suite
pytest tests/ -v

# 6. Run academic benchmark harness
python scripts/evaluate.py

# 7. Start local development server
python app.py
# Server running at http://127.0.0.1:5000
```

---

## 4. Vercel Serverless Deployment Architecture

The repository contains `vercel.json`:
```json
{
  "version": 2,
  "builds": [
    {
      "src": "app.py",
      "use": "@vercel/python"
    }
  ],
  "routes": [
    {
      "src": "/static/(.*)",
      "dest": "/static/$1"
    },
    {
      "src": "/(.*)",
      "dest": "app.py"
    }
  ]
}
```

Whenever commits are pushed to the `main` branch on GitHub, Vercel initiates an automated build, installs `requirements.txt`, and deploys globally with edge caching on static assets.
