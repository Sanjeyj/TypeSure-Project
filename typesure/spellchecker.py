"""
spellchecker.py — Core Tamil spell-checking logic.

Algorithm overview:
1. Tokenize input text using text_processing.tokenize().
2. For each Tamil token, check if it exists in the dictionary.
3. For unknown words, compute Levenshtein edit distance against dictionary
   candidates and rank them.
4. Return structured results including flagged words and suggestions.

Levenshtein edit distance:
  The edit distance between two strings is the minimum number of single-
  character edits (insertions, deletions, substitutions) needed to transform
  one string into the other. A distance of 1 means one typo; 2 means two
  edits, and so on. For Tamil words (typically 3–8 characters), a threshold
  of 2 catches common single- and double-character typing errors without
  producing too many irrelevant suggestions.

Performance note:
  Comparing an unknown word against every dictionary entry can be slow for
  large dictionaries. We apply a length filter first (only compare against
  words whose length differs by at most MAX_DISTANCE) to reduce the candidate
  pool significantly.
"""

import unicodedata
from typing import Optional
from .text_processing import tokenize, normalize
from .dictionary_loader import dictionary as tamil_dict

# Maximum Levenshtein distance to consider a suggestion "useful"
MAX_DISTANCE = 2

# Maximum number of suggestions to return per unknown word
MAX_SUGGESTIONS = 5

# Minimum Tamil word length to bother checking (avoids single-char particles)
MIN_CHECK_LENGTH = 2


# ---------------------------------------------------------------------------
# Common Tamil typing-error examples (manually verified)
# ---------------------------------------------------------------------------
# These pairs are illustrative; they do NOT exhaustively cover Tamil phonology.
# Format: (incorrect_form, correct_form, description)
COMMON_ERROR_EXAMPLES = [
    ("வணககம்", "வணக்கம்", "Missing க்க pulli (doubled consonant)"),
    ("நனடி", "நண்டி", "Missing ண் anusvara"),
    ("எழுது", "எழுதி", "Common vowel ending variation"),
    ("படிகிரேன்", "படிக்கிறேன்", "Missing pulli and ற"),
    ("சாபிடு", "சாப்பிடு", "Missing pulli on ப்"),
]


# ---------------------------------------------------------------------------
# Levenshtein distance (iterative, O(mn) time, O(min(m,n)) space)
# ---------------------------------------------------------------------------

def levenshtein(s1: str, s2: str) -> int:
    """
    Compute the Levenshtein edit distance between two strings.

    Uses the Wagner–Fischer dynamic-programming algorithm with a single
    array optimization to keep memory usage at O(min(len(s1), len(s2))).
    """
    if s1 == s2:
        return 0
    if not s1:
        return len(s2)
    if not s2:
        return len(s1)

    # Keep s1 as the shorter string for memory efficiency
    if len(s1) > len(s2):
        s1, s2 = s2, s1

    prev = list(range(len(s1) + 1))
    for ch2 in s2:
        curr = [prev[0] + 1]
        for j, ch1 in enumerate(s1):
            cost = 0 if ch1 == ch2 else 1
            curr.append(min(curr[j] + 1, prev[j + 1] + 1, prev[j] + cost))
        prev = curr
    return prev[-1]


# ---------------------------------------------------------------------------
# Candidate generation
# ---------------------------------------------------------------------------

def _candidates_for(word: str, max_dist: int = MAX_DISTANCE) -> list:
    """
    Return a list of (distance, dict_word) tuples for dictionary words that
    are within max_dist edits of `word`.

    The length-filter pre-step eliminates most candidates before the more
    expensive Levenshtein computation runs.
    """
    wlen = len(word)
    results = []
    for dw in tamil_dict.words:
        # Length filter: skip words whose length differs by more than max_dist
        if abs(len(dw) - wlen) > max_dist:
            continue
        d = levenshtein(word, dw)
        if d <= max_dist:
            results.append((d, dw))
    return results


def get_suggestions(word: str) -> list:
    """
    Return up to MAX_SUGGESTIONS ranked correction suggestions for `word`.

    Ranking:
      1. Edit distance (lower is better).
      2. Alphabetical order as a stable tiebreaker.

    Returns a list of dicts: [{"word": str, "distance": int}, ...]
    """
    word = normalize(word)
    candidates = _candidates_for(word)
    if not candidates:
        return []
    candidates.sort(key=lambda x: (x[0], x[1]))
    seen = set()
    suggestions = []
    for dist, w in candidates:
        if w not in seen:
            seen.add(w)
            suggestions.append({"word": w, "distance": dist})
        if len(suggestions) >= MAX_SUGGESTIONS:
            break
    return suggestions


# ---------------------------------------------------------------------------
# Main spell-check function
# ---------------------------------------------------------------------------

def check_text(text: str) -> dict:
    """
    Spell-check a Tamil text string.

    Parameters
    ----------
    text : str
        Raw user input (may contain Tamil, English, digits, punctuation).

    Returns
    -------
    dict with keys:
      - "spans"       : list of span dicts from tokenize()
      - "issues"      : list of issue dicts for flagged words
      - "stats"       : summary statistics
    """
    text = normalize(text)
    spans = tokenize(text)

    total_tamil = 0
    recognized = 0
    issues = []
    seen_words: dict = {}  # word → list of span indices with that word

    for i, span in enumerate(spans):
        if not span["is_tamil"]:
            continue
        word = span["text"]
        if len(word) < MIN_CHECK_LENGTH:
            # Very short particles — skip to reduce noise
            recognized += 1
            total_tamil += 1
            continue
        total_tamil += 1
        if tamil_dict.contains(word):
            recognized += 1
            span["status"] = "ok"
        else:
            span["status"] = "unknown"
            if word not in seen_words:
                seen_words[word] = []
            seen_words[word].append(i)

    # Build issues list (one entry per unique unknown word)
    for word, span_indices in seen_words.items():
        suggestions = get_suggestions(word)
        issues.append({
            "word": word,
            "span_indices": span_indices,
            "occurrences": len(span_indices),
            "suggestions": suggestions,
            "has_suggestions": bool(suggestions),
        })

    coverage_pct = round(recognized / total_tamil * 100, 1) if total_tamil else 0.0

    return {
        "spans": spans,
        "issues": issues,
        "stats": {
            "total_words_scanned": total_tamil,
            "issues_found": len(issues),
            "recognized": recognized,
            "dictionary_coverage_pct": coverage_pct,
            "dictionary_size": len(tamil_dict.words),
        },
    }
