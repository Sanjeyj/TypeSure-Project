# TypeSure — Intelligent Tamil Spelling Detection and Correction System

**B.Sc. Computer Science Final-Year Project**  
**Live Application**: [https://type-sure-project.vercel.app/](https://type-sure-project.vercel.app/)  
**GitHub Repository**: [https://github.com/Sanjeyj/TypeSure-Project](https://github.com/Sanjeyj/TypeSure-Project)  

---

## Abstract

**TypeSure** is a production-grade, privacy-centric Tamil language technology platform. Engineered specifically to tackle the linguistic challenges of Tamil Unicode orthography, agglutinative morphology, and phonological typing mistakes, TypeSure transforms academic research into a secure, scalable web platform.

### Core Engineering Innovations:
- **Unicode NFC Normalization & Grapheme Syllable Segmentation**: Treats orthographic syllables (அட்சரம்) as discrete linguistic units, handling base consonants, virama diacritics, aytham, and Grantha characters safely.
- **Burkhard-Keller (BK) Tree Metric Search**: Indexes 1,972 verified Tamil lemmas in an $n$-ary metric space tree using triangle inequality pruning for sub-linear fuzzy candidate retrieval ($1.30\times$ faster than linear scans).
- **Phonological & Orthographic Weighted Levenshtein Distance**: Uses a validated substitution penalty matrix for Tamil confusion groups: nasals (`ண`/`ன`/`ந`), rhotics (`ர`/`ற`), laterals/approximants (`ல`/`ள`/`ழ`), and vowel length pairs (`இ`/`ஈ`, `உ`/`ஊ`).
- **Agglutinative Morphology Engine**: Decomposes nominal cases (2nd–7th), plurals (`-கள்`/`-க்கள்`), and regular verbal conjugations (present, past, future), reducing false positive alarms to 0.00%.
- **Multi-Factor Candidate Ranking**: Combines integer distance, phonological penalty, grapheme Jaccard overlap, and token length ratios with calibrated confidence scoring.
- **OWASP-Hardened Application Security**: PBKDF2:SHA256 password hashing (600,000 rounds), sliding-window rate limiting on authentication endpoints (HTTP 429), parameterized SQL queries, strict session isolation, and Content Security Policy (CSP).
- **Brand Palette & Accessible Theme**: Forest Green (`#1F3D2B`), Sand Beige (`#E8DCC4`), and Electric Purple (`#8B5CF6`) with persistent light and dark modes.

---

## Empirical Benchmark Performance

Measured using `scripts/evaluate.py` across 52 standardized benchmark sentences and tokens:

| Metric | Baseline | Improved Production | Delta |
|---|:---:|:---:|:---:|
| **Active Dictionary Size** | 436 words | **1,972 verified lemmas** | **+1,536 lemmas (+352.3%)** |
| **Detection Precision** | 75.86% | **100.00%** | **+24.14% (Zero False Alarms)** |
| **Detection Recall** | 100.00% | **100.00%** | **0.00% (All Errors Caught)** |
| **Detection F1-Score** | 86.27% | **100.00%** | **+13.73%** |
| **Word-Level Top-1 Accuracy** | 77.27% | **100.00% (17/17)** | **+22.73%** |
| **Word-Level Top-5 Accuracy** | 77.27% | **100.00% (17/17)** | **+22.73%** |
| **BK-Tree Search Latency** | 1.48 ms | **7.16 ms** | Scalable metric tree across 1,972 words |
| **Automated Pytest Suite** | 112 passed | **138 passed** | **100.00% Test Pass Rate** |

---

## Comprehensive Technical Documentation Suite

Detailed technical reports and architectural specifications are available in `docs/`:

1. [Technical Audit & Baseline Report](docs/TECHNICAL_AUDIT.md) — Root causes, bottlenecks, baseline measurements.
2. [System Architecture Documentation](docs/ARCHITECTURE.md) — Layered architectural diagrams, component breakdown.
3. [Tamil NLP Engine Reference](docs/TAMIL_NLP_ENGINE.md) — Grapheme segmentation, morphology decomp, sandhi rules.
4. [Dictionary Sources & Provenance](docs/DICTIONARY_SOURCES.md) — Corpus breakdown, licensing, intake rules.
5. [Algorithm Comparison](docs/ALGORITHM_COMPARISON.md) — Metric space mathematical formulations, BK-tree vs Linear.
6. [Accuracy Evaluation Report](docs/ACCURACY_EVALUATION.md) — Detailed benchmark analysis, confusion matrices.
7. [Security Audit & Hardening Report](docs/SECURITY_AUDIT.md) — OWASP Top 10 matrix, rate limiting, access controls.
8. [Database Design & Reliability](docs/DATABASE_DESIGN.md) — Schemas, indexes, serverless path resolution.
9. [Automated Test Report](docs/TEST_REPORT.md) — Full pytest test suite execution logs.
10. [Production Deployment Guide](docs/DEPLOYMENT_GUIDE.md) — Vercel serverless instructions, CI/CD pipeline.

---

## Quick Start & Local Setup

```bash
# 1. Clone repository
git clone https://github.com/Sanjeyj/TypeSure-Project.git
cd TypeSure-Project

# 2. Setup virtual environment
python -m venv venv
source venv/bin/activate       # On Linux/macOS
# or: .\venv\Scripts\Activate.ps1 # On Windows

# 3. Install pinned dependencies
pip install -r requirements.txt

# 4. Compile Tamil dictionary index
python scripts/build_dictionary.py

# 5. Run full test suite (138 tests)
pytest tests/ -v

# 6. Run academic benchmark harness
python scripts/evaluate.py

# 7. Start local server
python app.py
# Open http://127.0.0.1:5000 in your browser
```

---

## CI / CD Pipeline

TypeSure includes a continuous integration workflow configured under `.github/workflows/ci.yml`. On every push and pull request, the pipeline:
1. Installs pinned dependencies across Python 3.11 and 3.12.
2. Validates bytecode syntax.
3. Executes the 138-test automated pytest suite.
4. Executes the academic Tamil NLP benchmark harness.
5. Verifies output artifacts (`data/evaluation_results.csv`, `reports/baseline_vs_improved.csv`).
