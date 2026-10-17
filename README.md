# TypeSure — Tamil Spelling Detection and Correction System

> A B.Sc. Computer Science final-year project that helps users identify and correct potential spelling mistakes in Tamil text using dictionary lookup, Unicode-aware text processing, and edit-distance algorithms.

---

## Table of Contents

1. [Project Overview](#project-overview)
2. [Problem Statement](#problem-statement)
3. [Objectives](#objectives)
4. [Scope](#scope)
5. [Architecture](#architecture)
6. [Modules](#modules)
7. [Algorithms](#algorithms)
8. [Database Schema](#database-schema)
9. [Software & Hardware Requirements](#software--hardware-requirements)
10. [Installation](#installation)
11. [Running the Project](#running-the-project)
12. [Running Tests](#running-tests)
13. [Example Inputs & Outputs](#example-inputs--outputs)
14. [API Reference](#api-reference)
15. [Limitations](#limitations)
16. [Future Enhancements](#future-enhancements)
17. [Privacy & Security](#privacy--security)

---

## Project Overview

TypeSure is a Tamil-language spelling detection and correction prototype. It processes Tamil Unicode text locally on a Flask server, compares each token against a starter dictionary, and suggests corrections based on Levenshtein edit distance. No paid API, cloud service, or machine-learning model is required.

---

## Problem Statement

Tamil speakers who type in Unicode Tamil often make common mistakes:
- Missing *pulli* (virama/halant) marks that shorten a consonant.
- Incorrect vowel endings (e.g., -இ vs -ஈ).
- Typographic errors from keyboard layout unfamiliarity.

Unlike English, most text editors do not include a Tamil spell checker. TypeSure provides a simple, explainable starting point for Tamil spelling assistance.

---

## Objectives

1. Implement Tamil Unicode tokenization that does not corrupt multi-byte characters.
2. Provide dictionary-based spell checking using a curated starter word list.
3. Rank and display correction suggestions using Levenshtein edit distance.
4. Allow users to interactively accept or reject suggestions without automatic replacement.
5. Store anonymous session statistics in SQLite.
6. Deliver a clean, responsive web interface with Tamil font support.
7. Achieve meaningful automated test coverage of the core logic.

---

## Scope

**In scope:**
- Common Tamil word forms (nouns, verbs, adjectives, pronouns, inflected forms).
- Keyboard typing errors (missing characters, wrong characters).
- Mixed Tamil-English text (English words are skipped).
- Local/offline operation.

**Out of scope:**
- Full Tamil grammar checking.
- Context-aware semantic correction.
- Morphological analysis or agglutinative word decomposition.
- Support for Tamil dialects or classical Tamil (Senthamizh).
- Real-time keypress analysis.

---

## Architecture

```
Browser (HTML + CSS + JS)
        │  HTTP (JSON / multipart)
        ▼
Flask Web Server (app.py)
        │
        ├─── text_processing.py  → tokenize, normalize
        ├─── spellchecker.py     → check, Levenshtein, suggestions
        ├─── dictionary_loader.py → in-memory set, import
        └─── database.py         → SQLite history (parameterized SQL)
                │
                └─── data/typesure.db  (SQLite file)
                └─── data/ta_dictionary.txt (starter word list)
```

---

## Modules

| File | Purpose |
|------|---------|
| `app.py` | Flask routes, request validation, error handlers |
| `typesure/text_processing.py` | Unicode NFC normalization, tokenization, token-type detection |
| `typesure/spellchecker.py` | Levenshtein distance, candidate generation, `check_text()` |
| `typesure/dictionary_loader.py` | `TamilDictionary` class, import validation, singleton |
| `typesure/database.py` | SQLite `checks` table: save, query, delete, stats |
| `data/ta_dictionary.txt` | Curated starter Tamil word list |
| `templates/index.html` | Main editor page |
| `templates/about.html` | Project description and algorithm explanations |
| `static/css/style.css` | Responsive stylesheet with Tamil font support |
| `static/js/app.js` | Frontend logic: check, render, correct, undo, history, import |
| `tests/` | Automated pytest test suite |

---

## Algorithms

### 1. Unicode NFC Normalization
Tamil text stored on different platforms may use different Unicode representations for the same character. NFC (Canonical Decomposition followed by Canonical Composition) guarantees a consistent canonical form before any string comparison is performed. Implemented using Python's `unicodedata.normalize("NFC", text)`.

### 2. Tokenization (Regular Expression–Based)
The input text is scanned with a regular expression that matches:
- Tamil Unicode sequences: `[\u0B80-\u0BFF]+`
- Latin/English words: `[A-Za-z]+`
- Digit runs: `[0-9]+`
- Single punctuation marks

Each match is assigned a start/end character position (span) so the frontend can highlight the exact location of each potential issue.

### 3. Dictionary Lookup (O(1) Hash Set)
The starter dictionary is loaded from `data/ta_dictionary.txt` into a Python `set`. Set membership testing is O(1) average-case. A word is considered "recognized" if its NFC-normalized form is in this set.

### 4. Levenshtein Edit Distance
For each unrecognized Tamil word, the system searches for close dictionary entries using the Wagner–Fischer dynamic-programming algorithm:

```
Given strings s1 (length m) and s2 (length n):
- Create a 1-D array prev of size m+1, initialized to [0,1,2,...,m].
- For each character c2 in s2:
    - Create curr[0] = prev[0] + 1
    - For j = 0 to m-1:
        cost = 0 if s1[j] == c2 else 1
        curr[j+1] = min(curr[j]+1, prev[j+1]+1, prev[j]+cost)
    - prev = curr
- Return prev[m]
```

Time: O(m × n) · Space: O(min(m, n))

### 5. Candidate Pre-filtering
Before computing Levenshtein distance, candidates whose length differs from the query by more than the threshold (default: 2) are eliminated. For a dictionary of N words, this typically reduces comparisons by 70–90%.

### 6. Suggestion Ranking
Remaining candidates are sorted by:
1. Edit distance (ascending)
2. Alphabetical order (stable tiebreaker)

Up to 5 suggestions are returned per unknown word.

---

## Database Schema

```sql
CREATE TABLE checks (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    created_at  TEXT    NOT NULL,   -- ISO-8601 UTC timestamp
    word_count  INTEGER NOT NULL,   -- Tamil words scanned
    issue_count INTEGER NOT NULL,   -- potential issues found
    corrections INTEGER NOT NULL DEFAULT 0,  -- corrections accepted
    store_text  INTEGER NOT NULL DEFAULT 0,  -- 1 = user opted in
    input_text  TEXT    -- NULL unless store_text = 1
);
```

All queries use `?` parameterized placeholders (no string interpolation).

---

## Software & Hardware Requirements

**Software:**
- Python 3.10 or later
- pip
- A modern web browser (Chrome, Firefox, Edge, Safari)
- Internet access only for loading Google Fonts (optional — falls back gracefully)

**Hardware:**
- Any standard laptop or desktop computer
- Minimum 512 MB RAM
- No GPU required

---

## Installation

```bash
# 1. Navigate to the project directory
cd TypeSure

# 2. (Recommended) Create a virtual environment
python -m venv venv

# 3. Activate the virtual environment
# Windows:
venv\Scripts\activate
# macOS/Linux:
source venv/bin/activate

# 4. Install dependencies
pip install -r requirements.txt
```

---

## Running the Project

```bash
# From the TypeSure directory with venv active:
python app.py
```

The server starts at **http://127.0.0.1:5000**

To enable debug mode (development only):
```bash
FLASK_DEBUG=1 python app.py
```

---

## Running Tests

```bash
# From the TypeSure directory:
python -m pytest tests/ -v
```

Expected output: all tests pass. See test results below for verification.

---

## Example Inputs & Outputs

### Input (with errors)
```
வணககம். நான் தமழ் படிகிறேன்.
```

### Expected Output (flagged words)
| Word | Issue | Suggestion |
|------|-------|------------|
| வணககம் | Not in dictionary | வணக்கம் (d=2) |
| தமழ் | Not in dictionary | தமிழ் (d=1) |
| படிகிறேன் | Not in dictionary | படிக்கிறேன் (d=1) |

### Input (no errors)
```
வணக்கம். நான் தமிழ் படிக்கிறேன்.
```
Result: 0 issues found. Dictionary coverage: 100%.

---

## API Reference

| Method | Route | Description |
|--------|-------|-------------|
| GET | `/` | Main editor page |
| GET | `/about` | About / limitations page |
| POST | `/api/check` | Spell-check text (JSON body: `{"text": "..."}`) |
| GET | `/api/history` | Recent check history |
| DELETE | `/api/history` | Clear all history |
| POST | `/api/dictionary/import` | Upload a .txt word list |
| GET | `/api/report` | Download report (`?format=csv` or `?format=txt`) |
| GET | `/api/stats` | Dictionary and DB summary statistics |

---

## Limitations

1. **Limited dictionary:** The starter vocabulary covers common words but not the full Tamil lexicon.
2. **No morphological analysis:** Inflected forms must be explicitly listed.
3. **No grammar checking:** Only individual word spelling is checked.
4. **Edit distance is language-agnostic:** The algorithm treats all character edits as equal cost; Tamil-specific phoneme relationships are not modeled.
5. **Short-word noise:** Very short Tamil particles (1 character) are skipped to reduce false positives.
6. **Not for production:** This is a student prototype.

---

## Future Enhancements

1. Integrate a comprehensive word list (Wiktionary Tamil dump, OLTools).
2. Add morphological root analysis for agglutinative forms.
3. Implement Tamil phonetic similarity scoring.
4. Context-aware n-gram ranking of suggestions.
5. Browser extension for system-wide spelling assistance.
6. User-specific custom dictionaries with persistence.
7. Offline font bundling for air-gapped environments.

---

## Privacy & Security

- Text is processed entirely on the local Flask server.
- No data is sent to any external API.
- Full input text is only stored in SQLite when the user explicitly opts in.
- All SQL uses parameterized queries.
- File uploads are restricted to `.txt`, validated for UTF-8, and size-limited to 2 MB.
- User content is never inserted into the DOM via `innerHTML` — only `textContent` is used.
- Maximum request size: 4 MB (enforced by Flask).
- Maximum text length: 20,000 characters (enforced in `/api/check`).

---

*TypeSure — Tamil Spelling Detection and Correction System*  
*B.Sc. Computer Science Final-Year Project*
