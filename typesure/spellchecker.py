"""
typesure/spellchecker.py — Core Tamil Spell-Checking & Correction Pipeline.

Algorithm Pipeline:
-------------------
1. Unicode Normalization: Canonical NFC normalization via text_processing.normalize().
2. Grapheme-Aware Tokenization: Span-preserving token separation.
3. Multi-Stage 7-Level Recognition Hierarchy:
   - Level 1: VERIFIED_WORD (O(1) lookup in verified 12,500+ Tamil lexicon)
   - Level 2: PERSONAL_DICTIONARY_WORD (User custom saved vocabulary)
   - Level 3: VALID_MORPHOLOGICAL_FORM (Inflected form of valid root: plural, case markers, clitics)
   - Level 4: VALID_COMPOUND (Sandhi/compound words composed of dictionary lemmas)
   - Level 5: KNOWN_VARIANT (Recognized orthographic/honorific variants like ஸ்ரீ)
   - Level 6: UNKNOWN_WORD (Phonotactically valid words not in dictionary; displayed as
              "Unrecognized word – Please review", NOT marked as a misspelling)
   - Level 7: POSSIBLE_SPELLING_ERROR (Close phonetic/Levenshtein edit-distance match to dictionary entries)
4. Candidate Search:
   - BK-Tree metric tree search for discrete Levenshtein candidates (d <= 2).
   - Linear length-filtered baseline fallback.
5. Intelligent Multi-Factor Candidate Ranking:
   - Evaluates weighted phonological distance, grapheme Jaccard overlap, and length ratio.
   - Constrained to the 3 best candidates with human-interpretable linguistic reasons.
"""

import time
from typing import List, Dict, Any, Optional, Set, Callable
from .text_processing import tokenize, normalize
from .dictionary_loader import dictionary as tamil_dict
from .ranking import rank_candidates
from .morphology import check_morphological_inflection
from .weighted_levenshtein import default_levenshtein
from .graphemes import split_graphemes
from .database import get_personal_word_set

MAX_DISTANCE = 2
MAX_SUGGESTIONS = 3
MIN_CHECK_LENGTH = 2

# Recognized common orthographic variants / honorifics
KNOWN_VARIANTS: Dict[str, str] = {
    "ஸ்ரீ": "Grantha honorific Sri",
    "ஶ்ரீ": "Grantha honorific Sri variant",
    "ஓம்": "Sacred Pranava syllable Om",
}


def check_compound_word(word: str, dict_contains_fn: Callable[[str], bool]) -> Optional[Dict]:
    """
    Detect if word is a valid compound (கூட்டுச்சொல்) composed of two dictionary roots,
    optionally bridged by a sandhi consonant (க், ச், த், ப்).
    Examples:
      தமிழ் + நாடு -> தமிழ்நாடு
      பள்ளி + கூடம் (with க் bridge) -> பள்ளிக்கூடம்
    """
    graphemes = split_graphemes(word)
    if len(graphemes) < 4:
        return None

    sandhi_bridges = {"க்", "ச்", "த்", "ப்"}

    for split_idx in range(2, len(graphemes) - 1):
        left = "".join(graphemes[:split_idx])
        right = "".join(graphemes[split_idx:])

        # Direct concatenation (e.g. தமிழ்நாடு)
        if dict_contains_fn(left) and dict_contains_fn(right):
            return {
                "is_compound": True,
                "parts": [left, right],
                "sandhi": None,
            }

        # Sandhi bridge consonant (e.g. பள்ளி + க் + கூடம்)
        if graphemes[split_idx] in sandhi_bridges and split_idx + 1 < len(graphemes):
            right_stem = "".join(graphemes[split_idx + 1:])
            if dict_contains_fn(left) and dict_contains_fn(right_stem):
                return {
                    "is_compound": True,
                    "parts": [left, right_stem],
                    "sandhi": graphemes[split_idx],
                }

    return None


def levenshtein(s1: str, s2: str) -> int:
    """Standard Levenshtein distance (re-exported for backwards compatibility)."""
    return default_levenshtein(s1, s2)


def get_suggestions(word: str, search_method: str = "bktree") -> List[Dict[str, Any]]:
    """
    Retrieve and rank the top 3 correction suggestions for an unknown Tamil word.
    """
    word = normalize(word)

    # 1. Candidate retrieval
    if search_method == "bktree":
        raw_candidates = tamil_dict.search_candidates_bktree(word, max_dist=MAX_DISTANCE)
    else:
        raw_candidates = tamil_dict.search_candidates_linear(word, max_dist=MAX_DISTANCE)

    if not raw_candidates:
        raw_candidates = tamil_dict.search_candidates_linear(word, max_dist=MAX_DISTANCE)

    candidate_dicts = [{"word": w, "distance": d} for d, w in raw_candidates]

    # 2. Multi-factor intelligent ranking, returning top 3 with reasons
    return rank_candidates(word, candidate_dicts, max_results=MAX_SUGGESTIONS)


def check_text(
    text: str,
    search_method: str = "bktree",
    user_id: Optional[int] = None,
) -> Dict[str, Any]:
    """
    Perform complete spell-checking and multi-stage recognition analysis on input text.

    Parameters:
    -----------
    text : str
        Raw input string (Tamil, English, digits, punctuation).
    search_method : str
        'bktree' (default, sub-linear) or 'linear' (exhaustive baseline).
    user_id : Optional[int]
        Authenticated user ID to check against their personal dictionary.

    Returns:
    --------
    dict containing:
      - 'spans'       : list of token span dicts with status and 7-stage classification
      - 'issues'      : list of unique unknown word issues with suggestions and reasons
      - 'stats'       : summary metrics (word counts, coverage, breakdown, latency)
    """
    start_time = time.perf_counter()

    text = normalize(text)
    spans = tokenize(text)

    # Retrieve user's personal dictionary if authenticated
    personal_words: Set[str] = get_personal_word_set(user_id) if user_id else set()

    total_tamil = 0
    recognized = 0
    verified_count = 0
    personal_recognized = 0
    morphology_recognized = 0
    compound_recognized = 0
    variant_recognized = 0

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
            span["classification"] = "VERIFIED_WORD"
            continue

        total_tamil += 1

        # 1. Exact match in verified master dictionary
        if tamil_dict.contains(word):
            recognized += 1
            verified_count += 1
            span["status"] = "ok"
            span["classification"] = "VERIFIED_WORD"
            continue

        # 2. Personal dictionary lookup (user-saved vocabulary)
        if word in personal_words:
            recognized += 1
            personal_recognized += 1
            span["status"] = "ok"
            span["classification"] = "PERSONAL_DICTIONARY_WORD"
            span["notes"] = "Recognized from your personal dictionary"
            continue

        # 3. Known variants / honorifics
        if word in KNOWN_VARIANTS:
            recognized += 1
            variant_recognized += 1
            span["status"] = "ok"
            span["classification"] = "KNOWN_VARIANT"
            span["description"] = KNOWN_VARIANTS[word]
            continue

        # 4. Morphological suffix analysis
        morph_info = check_morphological_inflection(word, tamil_dict.contains)
        if morph_info:
            recognized += 1
            morphology_recognized += 1
            span["status"] = "ok"
            span["classification"] = "VALID_MORPHOLOGICAL_FORM"
            span["morphology"] = morph_info
            continue

        # 5. Compound word decomposition (கூட்டுச்சொல்)
        compound_info = check_compound_word(word, tamil_dict.contains)
        if compound_info:
            recognized += 1
            compound_recognized += 1
            span["status"] = "ok"
            span["classification"] = "VALID_COMPOUND"
            span["compound"] = compound_info
            continue

        # Word not in any verified dictionary — track for candidate generation
        if word not in seen_words:
            seen_words[word] = []
        seen_words[word].append(i)

    # Multi-factor analysis for unrecognized words
    for word, span_indices in seen_words.items():
        suggestions = get_suggestions(word, search_method=search_method)

        # Distinguish between likely typo vs unrecognized vocabulary
        is_likely_typo = False
        if suggestions:
            top_cand = suggestions[0]
            # Likely typo if raw distance == 1 or phonological weighted distance <= 0.85
            if top_cand["distance"] == 1 or top_cand.get("weighted_distance", 2.0) <= 0.85:
                is_likely_typo = True

        classification = "POSSIBLE_SPELLING_ERROR" if is_likely_typo else "UNKNOWN_WORD"
        message = "Possible spelling error" if is_likely_typo else "Unrecognized word – Please review"

        for idx in span_indices:
            spans[idx]["status"] = "unknown"
            spans[idx]["classification"] = classification
            spans[idx]["message"] = message

        issues.append({
            "word": word,
            "span_indices": span_indices,
            "occurrences": len(span_indices),
            "classification": classification,
            "message": message,
            "suggestions": suggestions[:MAX_SUGGESTIONS],
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
            "verified_words": verified_count,
            "personal_words": personal_recognized,
            "morphology_recognized": morphology_recognized,
            "compound_recognized": compound_recognized,
            "variant_recognized": variant_recognized,
            "dictionary_coverage_pct": coverage_pct,
            "dictionary_size": len(tamil_dict.words),
            "processing_time_ms": elapsed_ms,
            "search_method": search_method,
        },
    }
