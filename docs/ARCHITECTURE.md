# TypeSure — System Architecture Documentation

**System Title**: Intelligent Tamil Spelling Detection and Correction System  
**Version**: 2.0.0 (Production Release)  
**Architecture Pattern**: Layered Modular SaaS / Metric-Space NLP Pipeline  

---

## 1. High-Level Architectural Diagram

```text
┌─────────────────────────────────────────────────────────────────────────────┐
│                          PRESENTATION LAYER (UI/UX)                         │
│  - Split-Screen Auth (Login / Register / Password Reset)                    │
│  - Tabbed Dashboard (Overview, Checker Workspace, Dictionary, History, ...) │
│  - Accessible Palette: Forest Green (#1F3D2B), Sand Beige (#E8DCC4),        │
│    Electric Purple (#8B5CF6)                                                │
│  - Persistent Light / Dark Mode System (LocalStorage & Anti-Flicker Script) │
└──────────────────────────────────────┬──────────────────────────────────────┘
                                       │ HTTPS / JSON REST API
┌──────────────────────────────────────▼──────────────────────────────────────┐
│                           API & APPLICATION LAYER                           │
│  - Flask Application Controller (app.py)                                    │
│  - Sliding-Window IP Rate Limiter (typesure/auth.py)                        │
│  - Route Guards (@login_required) & Session Authentication                  │
│  - Context Processor (User State & Navigation Injection)                    │
└──────────────────────────────────────┬──────────────────────────────────────┘
                                       │
     ┌─────────────────────────────────┴─────────────────────────────────┐
     ▼                                                                   ▼
┌─────────────────────────────────────────┐ ┌─────────────────────────────────────────┐
│         TAMIL NLP ENGINE LAYER          │ │          PERSISTENCE LAYER            │
│  - Unicode NFC Normalization            │ │  - SQLite Local & Serverless Path (/tmp)│
│  - Grapheme Cluster Segmentation        │ │  - Parameterized Query Isolation        │
│  - Agglutinative Morphological Analyzer │ │  - Tables: users, checks, custom_words │
│  - BK-Tree Metric Space Index           │ │  - Per-User Data Partitioning           │
│  - Phonological Weighted Levenshtein    │ └─────────────────────────────────────────┘
│  - Multi-Factor Candidate Ranker        │
└─────────────────────────────────────────┘
```

---

## 2. Component Breakdown

### 2.1 Web & Application Core (`app.py`)
- **Framework**: Flask 3.1+ running with WSGI compatibility on Vercel Edge Serverless functions.
- **Entry Routing**: Root `/` presents the split-screen **Login page first** for guests, seamlessly redirecting authenticated sessions to the internal `/dashboard`.
- **Public Reference**: `/landing` hosts the public feature overview, while `/about` details project objectives.

### 2.2 Tamil Computational Linguistics Modules (`typesure/`)
1. `typesure/text_processing.py`: Tokenizes mixed script inputs, preserves exact token spans (`start`, `end`), and handles abbreviations (e.g. `கி.மு.`, `திரு.`).
2. `typesure/graphemes.py`: Orthographic syllable parsing across Tamil vowels (உயிர்), consonants with virama (மெய்), vowel-consonants (உயிர்மெய்), aytham (ஆய்தம்), and Grantha scripts.
3. `typesure/morphology.py`: Decomposes nominal cases (2nd–7th), plural suffixes (`-கள்/-க்கள்`), and regular verbal conjugations (present `-கிறு`, past `-த்த/-ந்த`, future `-ப்/-வ்`).
4. `typesure/bktree.py`: Sub-linear discrete metric search tree satisfying identity, symmetry, and the triangle inequality.
5. `typesure/weighted_levenshtein.py`: Computes phonologically penalised distance over Tamil confusion axes (nasals `ண/ன/ந`, rhotics `ர/ற`, liquids `ல/ள/ழ`, vowel lengths).
6. `typesure/ranking.py`: Multi-factor candidate scoring combining normalized distance, phonological penalty, grapheme Jaccard overlap, and token length ratios.
7. `typesure/dictionary_loader.py`: Dual-index structure combining an $O(1)$ Python hash set with the BK-Tree index.

### 2.3 Authentication & Authorization (`typesure/auth.py`)
- PBKDF2:SHA256 password hashing with 600,000 rounds and dynamic salt.
- Sliding-window in-memory rate limiting preventing automated brute force.
- Backend authorization enforcing logical tenant isolation (`user_id`).

### 2.4 Database Subsystem (`typesure/database.py`)
- Dynamic database resolution: uses `data/typesure.db` in local environments and `/tmp/typesure.db` in serverless cloud environments where root directories are read-only.
- Idempotent table schemas and automatic schema migration.
