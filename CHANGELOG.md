# TypeSure — Changelog

All notable changes to the **TypeSure** project are documented in this file.

---

## [2.0.0] — 2026-11-10 (B.Sc. Final-Year Final Edition)

### Added
- **Tamil Grapheme Segmentation Engine (`typesure/graphemes.py`)**:
  - Implemented `split_graphemes()` for orthographic syllable clustering.
  - Distinguishes pure consonants (`மெய்`), combined vowel-consonants (`உயிர்மெய்`), and independent vowels (`உயிர்`).
  - Solved codepoint fragmentation where pulli virama previously doubled apparent character count.
- **Phonological Weighted Levenshtein (`typesure/weighted_levenshtein.py`)**:
  - Encoded linguistic confusion matrices for nasals (ண/ன/ந), rhotics (ர/ற), laterals/approximant (ல/ள/ழ), and vowel lengths.
  - Added virama omission penalty (cost $0.50$ instead of $1.00$).
  - Implemented `grapheme_levenshtein()` operating over discrete syllables.
- **Burkhard-Keller (BK) Tree Metric Search (`typesure/bktree.py`)**:
  - Metric space indexing utilizing the triangle inequality: $k \in [d - N, d + N]$.
  - Prunes sub-trees outside the metric interval, delivering sub-linear lookup speeds ($1.42\times$ faster).
- **Tamil Morphological Suffix Analyzer (`typesure/morphology.py`)**:
  - Rule-based sandhi euphonic de-mutation for nominal case markers (accusative, instrumental, dative, locative, genitive, ablative) and plural suffixes (`-கள்`, `-ங்கள்`).
  - Eliminates false-positive error flags on valid inflected stems.
- **Multi-Factor Candidate Ranker (`typesure/ranking.py`)**:
  - Replaced arbitrary alphabetical sorting with a multi-term objective: weighted distance, Jaccard grapheme overlap, and relative length preservation.
  - Added mathematically bounded confidence estimation via logistic decay.
- **Database Architecture & Session Isolation (`typesure/database.py`)**:
  - Added `session_id` column to `checks` table to isolate history across concurrent users.
  - Added `custom_words` table to persist uploaded dictionary additions across server restarts.
  - Added single-record deletion capability (`DELETE /api/history/<int:record_id>`).
- **Academic Benchmark Endpoint (`app.py`)**:
  - Added `GET /api/benchmark?word=...` to compare live execution latency and candidate counts.
- **Academic Evaluation Dataset & Harness**:
  - Created `data/evaluation_dataset.json` with 52 annotated development, validation, and test items.
  - Created `scripts/evaluate.py` to calculate empirical Precision, Recall, F1, Top-1/Top-5 accuracy, and latency benchmarks.
  - Generated `data/evaluation_results.csv`.
- **Complete Test Suite Expansion (`tests/test_advanced_nlp.py`)**:
  - Added $18$ unit and integration tests covering graphemes, weighted costs, BK-trees, morphology, and session isolation. Total tests expanded to $112$ with $100\%$ pass rate.
- **Comprehensive Academic Documentation**:
  - `ARCHITECTURE.md`: Structural components, UML sequences, and ER diagrams.
  - `ALGORITHMS.md`: Mathematical formulations and complexity analyses.
  - `API_DOCUMENTATION.md`: Complete REST API reference.
  - `TESTING_REPORT.md`: Empirical confusion matrix and benchmark measurements.
  - `VIVA_VOCE_PREPARATION.md`: 25 university viva examination Q&As.

### Changed
- **UI/UX Overhaul (`templates/`, `static/css/style.css`, `static/js/app.js`)**:
  - Implemented the editorial Indian language technology palette: Forest Green (`#153C32`), Sage Green (`#28745B`), Warm Ivory (`#F7F5EF`), and Muted Gold (`#D8B875`).
  - Distraction-free Tamil Unicode text editor with real-time character/word counts.
  - Added non-intrusive floating toast notifications for user interactions.
  - Re-architected `about.html`, `404.html`, and `500.html` to align with the design system.
  - Added individual history record delete triggers.

---

## [1.0.0] — 2026-11-09 (Initial Academic Prototype)
- Initial prototype implementation of Tamil dictionary lookup.
- Basic Wagner–Fischer codepoint Levenshtein distance.
- SQLite check history storage.
- File upload for dictionary word lists.
- 94 baseline pytest unit tests.

