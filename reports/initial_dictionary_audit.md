# TypeSure — Initial Dictionary Audit Report

**Date of Audit**: November 2026  
**Auditor**: Principal Software Engineer & Tamil Computational Linguistics Team  
**Scope**: Primary Dictionary Storage (`data/ta_dictionary.txt`), Database Custom Lexicon (`typesure.db`), In-Memory Set and BK-Tree Index  

---

## 1. Storage & Architecture Findings

1. **Storage Formats**:
   - Primary bundled vocabulary is maintained in `data/ta_dictionary.txt` as a single-entry-per-line UTF-8 plain text file.
   - User-added custom vocabulary is persisted in SQLite (`custom_words` table: `id`, `word`, `created_at`).
2. **Indexing Mechanism**:
   - `typesure/dictionary_loader.py` initializes an $O(1)$ Python hash set `self.words` for instant exact membership lookup.
   - A Burkhard-Keller metric tree (`BKTree`) is built over the vocabulary using standard Levenshtein distance ($d \le 2$) for sub-linear fuzzy candidate retrieval.
3. **Existing Word Counts**:
   - **Total Raw Lines**: 1,982 lines (including 10 metadata header comments and 1 blank line).
   - **Data Lines**: 1,971 entries in file + 1 persisted word in SQLite = **1,972 unique in-memory words**.
   - **Unicode Normalization**: All 1,971 file entries conform to Unicode NFC composition.
   - **Invalid Characters / Non-Tamil Tokens**: 0 invalid entries detected.
   - **Duplicate Count**: 0 duplicates in existing dataset.

---

## 2. Root Cause Analysis of False Positive Errors

Despite previous enhancements to 1,972 words, the root cause of false positives remains:

1. **Vocabulary Coverage Deficit**:
   - Standard Tamil adult literature and professional communication typically utilizes a lexicon exceeding 40,000 to 70,000 surface word forms.
   - 1,972 words cover high-frequency everyday vocabulary, but standard conversational, academic, technical, business, and administrative vocabulary not in this set is flagged.
2. **Binary Error Classification Failure**:
   - Current logic treats any word not found in the dictionary or morphological rule table as an `unknown` issue with status `unknown`, which the UI displays as an error.
   - **Linguistic Reality**: An unknown word is often a valid proper noun, geographical place, technical borrowing, or rare literary word, rather than an orthographic misspelling.
   - **Required Solution**: A multi-stage classification pipeline distinguishing `VERIFIED_WORD`, `VALID_MORPHOLOGICAL_FORM`, `VALID_COMPOUND`, `PERSONAL_DICTIONARY_WORD`, `KNOWN_VARIANT`, `UNKNOWN_WORD`, and `POSSIBLE_SPELLING_ERROR`.

---

## 3. Data Backup Artifacts

The existing vocabulary has been backed up into `exports/`:
- `exports/existing_dictionary.txt`: Plain text (1,972 entries).
- `exports/existing_dictionary.csv`: Structured CSV with NFC normalization and Unicode codepoints.
- `exports/existing_dictionary.json`: Complete structured JSON export with metadata.
