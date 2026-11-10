"""
typesure/spellchecker.py — Core Tamil Spell-Checking & Correction Pipeline.

Algorithm Pipeline:
-------------------
1. Unicode Normalization: Canonical NFC normalization via text_processing.normalize().
2. Grapheme-Aware Tokenization: Span-preserving token separation.
3. Exact Dictionary Lookup: O(1) set membership test.
4. Morphological Suffix Analysis: Detects valid nominal inflections (plural, cases)
   preventing false positives on valid inflected words.
5. Candidate Search:
   - BK-Tree metric tree search for discrete Levenshtein candidates (d <= 2).
   - Linear length-filtered baseline fallback.
6. Intelligent Multi-Factor Candidate Ranking:
   - Evaluates weighted phonological distance, grapheme Jaccard overlap, and length ratio.
7. Result Structuring: Returns spans, flagged issues, suggestions, and processing latency.
"""

import time
from typing import List, Dict, Any, Optional
from .text_processing import tokenize, normalize
from .dictionary_loader import dictionary as tamil_dict
from .ranking import rank_candidates
from .morphology import check_morphological_inflection
from .weighted_levenshtein import default_levenshtein

MAX_DISTANCE = 2
MAX_SUGGESTIONS = 5
MIN_CHECK_LENGTH = 2


def levenshtein(s1: str, s2: str) -> int:
    """Standard Levenshtein distance (re-exported for backwards compatibility)."""
    return default_levenshtein(s1, s2)


def get_suggestions(word: str, search_method: str = "bktree") -> List[Dict[str, Any]]:
    """
    Retrieve and rank correction suggestions for an unknown Tamil word.
    """
    word = normalize(word)

    # 1. Candidate retrieval
    if search_method == "bktree":
        raw_candidates = tamil_dict.search_candidates_bktree(word, max_dist=MAX_DISTANCE)
    else:
        raw_candidates = tamil_dict.search_candidates_linear(word, max_dist=MAX_DISTANCE)

    if not raw_candidates:
        # Fallback to linear if BK-tree returns empty for safety
        raw_candidates = tamil_dict.search_candidates_linear(word, max_dist=MAX_DISTANCE)

    candidate_dicts = [{"word": w, "distance": d} for d, w in raw_candidates]

    # 2. Multi-factor intelligent ranking
    return rank_candidates(word, candidate_dicts, max_results=MAX_SUGGESTIONS)


def check_text(text: str, search_method: str = "bktree") -> Dict[str, Any]:
    """
    Perform complete spell-checking and correction analysis on input text.

    Parameters:
    -----------
    text : str
        Raw input string (Tamil, English, digits, punctuation).
    search_method : str
        'bktree' (default, sub-linear) or 'linear' (exhaustive baseline).

    Returns:
    --------
    dict containing:
      - 'spans'       : list of token span dicts
      - 'issues'      : list of unique unknown word issues with suggestions
      - 'stats'       : summary metrics (word counts, coverage, latency)
    """
    start_time = time.perf_counter()

    text = normalize(text)
    spans = tokenize(text)

    total_tamil = 0
    recognized = 0
    morphology_recognized = 0
    issues = []
    seen_words: Dict[str, List[int]] = {}

    for i, span in enumerate(spans):
        if not span["is_tamil"]:
            continue

        word = span["text"]
        if len(word) < MIN_CHECK_LENGTH:
            # Single-character particles/vowels
            recognized += 1
            total_tamil += 1
            span["status"] = "ok"
            continue

        total_tamil += 1

        # 1. Exact dictionary match
        if tamil_dict.contains(word):
            recognized += 1
            span["status"] = "ok"
            continue

        # 2. Morphological suffix analysis
        morph_info = check_morphological_inflection(word, tamil_dict.contains)
        if morph_info:
            recognized += 1
            morphology_recognized += 1
            span["status"] = "ok"
            span["morphology"] = morph_info
            continue

        # 3. Flagged as potential spelling issue
        span["status"] = "unknown"
        if word not in seen_words:
            seen_words[word] = []
        seen_words[word].append(i)

    # Generate suggestions for each unique unknown word
    for word, span_indices in seen_words.items():
        suggestions = get_suggestions(word, search_method=search_method)
        issues.append({
            "word": word,
            "span_indices": span_indices,
            "occurrences": len(span_indices),
            "suggestions": suggestions,
            "has_suggestions": bool(suggestions),
        })

    elapsed_ms = round((time.perf_counter() - start_time) * 1000, 2)
    coverage_pct = round(recognized / total_tamil * 100, 1) if total_tamil else 0.0

    return {
        "spans": spans,
        "issues": issues,
        "stats": {
            "total_words_scanned": total_tamil,
            "issues_found": len(issues),
            "recognized": recognized,
            "morphology_recognized": morphology_recognized,
            "dictionary_coverage_pct": coverage_pct,
            "dictionary_size": len(tamil_dict.words),
            "processing_time_ms": elapsed_ms,
            "search_method": search_method,
        },
    }
