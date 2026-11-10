# TypeSure — Intelligent Tamil Spelling Detection and Correction System

**B.Sc. Computer Science Final-Year Project**  
**Live Application**: [https://type-sure-project.vercel.app/](https://type-sure-project.vercel.app/)  
**GitHub Repository**: [https://github.com/Sanjeyj/TypeSure-Project](https://github.com/Sanjeyj/TypeSure-Project)  

---

## Abstract

**TypeSure** is an intelligent language technology application engineered specifically for the Tamil language. It addresses the unique linguistic challenges of Tamil Unicode orthography, agglutinative morphology, and phonological keyboard typing mistakes. 

Traditional spelling checkers designed for Latin scripts fail on Tamil due to multi-codepoint grapheme clusters and agglutinative noun inflections. TypeSure introduces:
- **Unicode NFC Normalization & Grapheme Syllable Segmentation**: Treats orthographic syllables (அட்சரம்) as discrete units rather than splitting base consonants and virama diacritics.
- **Burkhard-Keller (BK) Tree Metric Search**: Indexes vocabulary words into an $n$-ary metric tree using triangle inequality pruning for sub-linear fuzzy retrieval ($1.42\times$ faster than linear scans).
- **Phonological & Orthographic Weighted Levenshtein Distance**: Discounts confusion pairs across nasals (`ண`/`ன`/`ந`), rhotics (`ர`/`ற`), and laterals (`ல`/`ள`/`ழ`), and penalizes missing pulli virama marks with custom substitution matrices.
- **Morphological Suffix Stripping**: Inverts regular sandhi euphonic mutations for case markers and plurals, preventing valid inflected stems from being flagged as errors.
- **Multi-Factor Candidate Ranking**: Combines phonological distance, Jaccard grapheme overlap, and relative word length with calibrated confidence decay.
- **Premium Editorial UI/UX**: Designed using an Indian Language Technology aesthetic in Forest Green (`#153C32`), Sage Green (`#28745B`), Warm Ivory (`#F7F5EF`), and Muted Gold (`#D8B875`).

---

## Table of Contents

1. [Problem Statement](#problem-statement)
2. [Objectives](#objectives)
3. [System Architecture](#system-architecture)
4. [Linguistic & Algorithmic Modules](#linguistic--algorithmic-modules)
5. [Empirical Evaluation & Benchmarks](#empirical-evaluation--benchmarks)
6. [Database & Security Engineering](#database--security-engineering)
7. [Installation & Local Setup](#installation--local-setup)
8. [Automated Test Suite](#automated-test-suite)
9. [API Reference Summary](#api-reference-summary)
10. [Academic Presentation & Viva Voce](#academic-presentation--viva-voce)

---

## 1. Problem Statement

Typing Tamil in modern digital environments frequently causes characteristic orthographic mistakes:
1. **Pulli (Virama) Omission**: Missing consonant doubling or virama marks (e.g., `வணககம்` instead of `வணக்கம்`).
2. **Phonological Confusion**: Ambiguity between retroflex, alveolar, and dental nasals (`ண`, `ன`, `ந`) and liquid consonants (`ல`, `ள`, `ழ`).
3. **Multi-Codepoint Distortion**: Standard string metrics evaluate Tamil codepoint by codepoint. For example, `கி` (`U+0B95` + `U+0BC0`) is evaluated as two separate ASCII-equivalent bytes, misrepresenting character error distances.
4. **Agglutinative False Positives**: In Tamil, nouns inflect with case and plural suffixes (e.g., `கல்லூரி` $\to$ `கல்லூரியில்`). Without morphology, standard dictionaries flag all inflections as spelling errors.

---

## 2. Objectives

1. Develop a grapheme-aware Unicode processing engine for Tamil script (`U+0B80–U+0BFF`).
2. Construct a Burkhard-Keller (BK) metric space tree for sub-linear fuzzy candidate retrieval.
3. Build a phonological weighted edit-distance matrix reflecting Tamil phonetic confusion classes.
4. Implement sandhi-aware morphological suffix decomposition for plurals and nominal cases.
5. Engineer a multi-factor candidate ranker with calibrated confidence scoring.
6. Provide an editorial web interface with real-time analytics and session-isolated history.
7. Validate performance empirically using a 52-item benchmark dataset.

---

## 3. System Architecture

```
+--------------------------------------------------------------------------+
|                               CLIENT LAYER                               |
|   HTML5 / CSS3 (Editorial SaaS Design System) / Vanilla ES6 JavaScript  |
|   - Distraction-Free Tamil Unicode Editor                                |
|   - Real-Time Syllable / Word / Character Counter                        |
|   - Interactive Suggestion Adoption & Undo Management                    |
|   - Responsive Desktop / Tablet / Mobile Layout                          |
+--------------------------------------------------------------------------+
                                     │
                                     │ HTTPS / JSON (RESTful API)
                                     ▼
+--------------------------------------------------------------------------+
|                             FLASK APPLICATION                            |
|   - Security Headers (CSP, Strict-Transport-Security, XSS Protection)    |
|   - Client Session Isolation Manager (X-Session-ID / Signed Cookie)      |
|   - Centralized Input Sanitization & Request Validation                  |
+--------------------------------------------------------------------------+
                                     │
         ┌───────────────────────────┴───────────────────────────┐
         ▼                                                       ▼
+------------------------------------+   +------------------------------------+
|          TAMIL NLP ENGINE          |   |         PERSISTENCE LAYER          |
| - Unicode NFC Normalization        |   | SQLite (WAL Mode) / /tmp Fallback  |
| - Grapheme Syllable Segmentation   |   | - checks (Session Isolated)        |
| - Morphological Suffix Analysis    |   | - custom_words (Persistent DB)     |
| - Burkhard-Keller (BK) Tree        |   | - Automated Schema Migrations      |
| - Phonological Weighted Matrix     |   +------------------------------------+
| - Multi-Factor Candidate Ranker    |
+------------------------------------+
```

Detailed architectural diagrams and sequence flows are documented in [ARCHITECTURE.md](ARCHITECTURE.md).

---

## 4. Linguistic & Algorithmic Modules

### 4.1 Unicode NFC & Grapheme Clustering (`typesure/graphemes.py`)
Orthographic syllables (அட்சரம்) are segmented using regular expressions:
$$\text{Grapheme} = (C + V_{\text{sign}}) \mid (C + \text{Virama}) \mid V_{\text{indep}} \mid \text{Aytham}$$
This ensures operations count `க்` and `கி` as single linguistic units rather than 2 disjoint characters.

### 4.2 BK-Tree Metric Space Index (`typesure/bktree.py`)
Levenshtein distance satisfies all metric space axioms. The BK-Tree utilizes the triangle inequality to prune branches whose edge distances fall outside $[d - N, d + N]$ for search radius $N=2$.

### 4.3 Weighted Phonological Matrix (`typesure/weighted_levenshtein.py`)
- Nasals (`ண` $\leftrightarrow$ `ன` $\leftrightarrow$ `ந`): Cost $0.55$
- Rhotics (`ர` $\leftrightarrow$ `ற`): Cost $0.55$
- Laterals (`ல` $\leftrightarrow$ `ள` $\leftrightarrow$ `ழ`): Cost $0.55$
- Pulli virama omission (`க` $\leftrightarrow$ `க்`): Cost $0.50$
- Standard character substitutions: Cost $1.00$

### 4.4 Morphological Suffix Decomposition (`typesure/morphology.py`)
Decomposes nominal suffixes while reversing sandhi mutations:
- Plural: `-கள்`, `-ங்கள்` $\to$ `-ம்` (`படங்கள்` $\to$ `படம்`)
- Locative: `-இல்`, `-யில்`, `-த்தில்` $\to$ `-ம்` (`கல்லூரியில்` $\to$ `கல்லூரி`)
- Accusative: `-ஐ`, `-\u0BC8` $\to$ `-\u0BCD` (`தமிழை` $\to$ `தமிழ்`)

### 4.5 Multi-Factor Candidate Ranking (`typesure/ranking.py`)
$$\text{Score} = 0.45 \cdot \frac{d_{\text{edit}}}{3} + 0.30 \cdot \frac{d_{\text{phon}}}{3} + 0.15 \cdot d_{\text{Jaccard}} + 0.10 \cdot \text{LengthRatio}$$
Calibrated confidence is computed via logistic decay: $\text{Confidence} = \frac{1}{1 + 0.8 \cdot d_{\text{phon}}}$.

Mathematical derivations and proofs are documented in [ALGORITHMS.md](ALGORITHMS.md).

---

## 5. Empirical Evaluation & Benchmarks

Empirically evaluated using `scripts/evaluate.py` across 52 test items (`data/evaluation_dataset.json`):

| Metric | Result | Description |
| :--- | :---: | :--- |
| **Detection Recall** | **$100.00\%$** | $22 / 22$ errors correctly identified |
| **Detection Precision** | **$75.86\%$** | Valid words correctly separated from errors |
| **Detection F1-Score** | **$86.27\%$** | Harmonic mean of precision and recall |
| **Correction Top-1 Accuracy** | **$77.27\%$** | Target word was the primary suggestion |
| **Correction Top-5 Accuracy** | **$77.27\%$** | Target word in top-5 candidates |
| **Average Linear Search Latency** | $3.542\text{ ms}$ | Baseline length-filtered iteration |
| **Average BK-Tree Search Latency** | **$2.501\text{ ms}$** | **$1.42\times$ search speedup** |

Detailed confusion matrices and evaluation reports are in [TESTING_REPORT.md](TESTING_REPORT.md).

---

## 6. Database & Security Engineering

- **Session Isolation**: Check histories are isolated per client session using `session_id` cookies and `X-Session-ID` headers.
- **Zero-Leak Default**: By default, `store_text = 0`; full text is never persisted unless the user explicitly opts in.
- **Content Security Policy (CSP)**:
  ```http
  Content-Security-Policy: default-src 'self'; style-src 'self' 'unsafe-inline' https://fonts.googleapis.com; font-src 'self' https://fonts.gstatic.com; script-src 'self';
  ```
- **Serverless Resilience**: Auto-detects Vercel deployment environments and maps the SQLite database to `/tmp/typesure.db` with automated schema migrations.

---

## 7. Installation & Local Setup

### Prerequisites
- Python 3.10+ (tested through Python 3.14)
- Git

### Installation Steps
```bash
# 1. Clone the repository
git clone https://github.com/Sanjeyj/TypeSure-Project.git
cd TypeSure-Project

# 2. Create and activate a virtual environment
python -m venv venv
# On Windows:
venv\Scripts\activate
# On Linux/macOS:
source venv/bin/activate

# 3. Install dependencies
pip install -r requirements.txt

# 4. Start the Flask application
python app.py
```
Open [http://localhost:5000](http://localhost:5000) in your browser.

---

## 8. Automated Test Suite

TypeSure features **112 automated tests** with $100\%$ pass rate:
```bash
pytest tests/ -v
```
Test modules:
- `tests/test_advanced_nlp.py`: Graphemes, weighted costs, BK-trees, morphology, and session isolation.
- `tests/test_routes.py`: Flask API endpoints, security headers, file uploads, and reports.
- `tests/test_spellchecker.py`: Baseline normalization, Levenshtein distance, and dictionary state.
- `tests/test_text_processing.py`: Tokenization spans, word counts, and edge cases.

---

## 9. API Reference Summary

| Method | Endpoint | Description |
| :--- | :--- | :--- |
| `POST` | `/api/check` | Analyze Tamil text, identify errors, and generate ranked suggestions |
| `GET` | `/api/history` | Retrieve session-isolated check history |
| `DELETE` | `/api/history` | Clear history for the current session |
| `DELETE` | `/api/history/<id>` | Delete an individual history record |
| `POST` | `/api/dictionary/import` | Upload and persist custom `.txt` word lists (max 2 MB) |
| `GET` | `/api/stats` | Retrieve dictionary size and database summary metrics |
| `GET` | `/api/benchmark` | Empirical benchmark comparing BK-tree vs linear lookup |
| `GET` | `/api/report?format=csv` | Export check history report as CSV or plain text |
| `GET` | `/healthz` | Deployment probe endpoint |

Complete API schemas and JSON payloads are documented in [API_DOCUMENTATION.md](API_DOCUMENTATION.md).

---

## 10. Academic Presentation & Viva Voce

For academic examiners and project defense preparations, see:
- [VIVA_VOCE_PREPARATION.md](VIVA_VOCE_PREPARATION.md): Contains 25 comprehensive technical questions and answers covering natural language processing, Unicode theory, metric spaces, algorithm complexity, and software architecture.
- [CHANGELOG.md](CHANGELOG.md): Detailed record of engineering iterations from prototype to v2.0 Final Edition.
