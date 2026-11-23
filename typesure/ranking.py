"""
typesure/ranking.py — Multi-Factor Candidate Ranking System.

Theoretical Background:
-----------------------
A naïve spelling checker sorts candidates purely by integer edit distance,
leading to arbitrary alphabetical ties between radically different words.
TypeSure uses a multi-factor scoring function:

  Score(candidate, query) =
      w_dist  * NormalizedDistance(candidate, query)
    + w_phon  * PhonologicalCost(candidate, query)
    + w_len   * LengthDifferenceRatio(candidate, query)
    + w_char  * JaccardGraphemeOverlap(candidate, query)

Lower scores indicate higher ranking candidates.
"""

from typing import List, Dict, Any
from .graphemes import split_graphemes, get_base_consonant
from .weighted_levenshtein import weighted_levenshtein, CONFUSION_GROUPS, VOWEL_SIGN_CONFUSIONS


def generate_suggestion_reason(query: str, candidate: str, weighted_dist: float) -> str:
    """
    Generate an interpretable linguistic explanation for why this candidate was suggested.
    Explains phonological confusions (ல/ள/ழ, ண/ன/ந, ர/ற), virama differences,
    vowel duration variations, or edit operations.
    """
    g_query = split_graphemes(query)
    g_cand = split_graphemes(candidate)

    # 1. Length differences (omission or extra letter)
    if len(g_cand) == len(g_query) + 1:
        # Check if difference is due to virama omission
        for q, c in zip(g_query, g_cand):
            if get_base_consonant(q) == get_base_consonant(c) and (q.endswith('\u0BCD') != c.endswith('\u0BCD')):
                return "Virama / Pulli omission (புள்ளி விடுபடல்)"
        return "Single letter omission (எழுத்து விடுபடல்)"
    elif len(g_cand) == len(g_query) - 1:
        return "Extra letter added (கூடுதல் எழுத்து)"

    # 2. Identical grapheme length substitutions
    if len(g_query) == len(g_cand):
        diffs = [(q, c) for q, c in zip(g_query, g_cand) if q != c]
        if len(diffs) == 1:
            q, c = diffs[0]
            bq, bc = get_base_consonant(q), get_base_consonant(c)
            # Lateral confusion (ல, ள, ழ)
            if bq in {"\u0BB2", "\u0BB3", "\u0BB4"} and bc in {"\u0BB2", "\u0BB3", "\u0BB4"}:
                return f"Phonological confusion: {bq} ↔ {bc} (ஒலி மயக்கம்: லகர/ளகர/ழகர)"
            # Nasal confusion (ண, ன, ந)
            if bq in {"\u0BA3", "\u0BA9", "\u0BA8"} and bc in {"\u0BA3", "\u0BA9", "\u0BA8"}:
                return f"Nasal confusion: {bq} ↔ {bc} (ணகர/னகர மயக்கம்)"
            # Rhotic confusion (ர, ற)
            if bq in {"\u0BB0", "\u0BB1"} and bc in {"\u0BB0", "\u0BB1"}:
                return f"Rhotic confusion: {bq} ↔ {bc} (ரகர/றகர மயக்கம்)"
            # Virama variation on same consonant
            if bq == bc:
                return "Virama / Pulli difference (மெய்யெழுத்து புள்ளி)"
            # Vowel sign duration difference
            if len(q) > 1 and len(c) > 1 and bq == bc:
                return "Vowel duration difference (குறில்/நெடில் வேறுபாடு)"
            for vgroup in VOWEL_SIGN_CONFUSIONS:
                if q in vgroup and c in vgroup:
                    return "Vowel length variation (குறில் ↔ நெடில்)"

    if weighted_dist < 0.8:
        return "High phonetic similarity (ஒலிப்பு ஒற்றுமை)"
    elif weighted_dist <= 1.2:
        return "Orthographic similarity (எழுத்து வடிவம்)"
    return "Closest dictionary match (அருகமைச் சொல்)"


def _grapheme_jaccard_distance(s1: str, s2: str) -> float:
    """Compute Jaccard distance between the sets of grapheme clusters."""
    g1 = set(split_graphemes(s1))
    g2 = set(split_graphemes(s2))
    if not g1 and not g2:
        return 0.0
    union_len = len(g1 | g2)
    if union_len == 0:
        return 0.0
    intersection_len = len(g1 & g2)
    similarity = intersection_len / union_len
    return 1.0 - similarity


def rank_candidates(
    query_word: str,
    candidates: List[Dict[str, Any]],
    max_results: int = 3,
) -> List[Dict[str, Any]]:
    """
    Rank suggestion candidates using weighted multi-factor scoring.
    Limits to the best top candidates (default 3) and attaches linguistic reason.

    Parameters:
    -----------
    query_word : str
        The misspelled input word.
    candidates : list of dicts
        Each candidate has {"word": str, "distance": int} (or float).
    max_results : int
        Maximum number of suggestions to return (default 3).

    Returns:
    --------
    List of ranked candidate dicts with 'word', 'distance', 'weighted_distance',
    'confidence', 'score', and 'reason'.
    """
    if not candidates:
        return []

    q_len = max(len(query_word), 1)
    scored = []

    for cand in candidates:
        word = cand["word"]
        dist = cand["distance"]

        # 1. Phonological weighted edit distance
        phon_dist = weighted_levenshtein(query_word, word)

        # 2. Grapheme Jaccard distance
        g_dist = _grapheme_jaccard_distance(query_word, word)

        # 3. Normalized length difference
        len_diff = abs(len(word) - q_len) / max(len(word), q_len)

        # Composite penalty score (lower is better)
        composite_score = (
            0.45 * (dist / 3.0) +
            0.30 * (phon_dist / 3.0) +
            0.15 * g_dist +
            0.10 * len_diff
        )

        # Calculate a calibrated confidence score (0.0 to 1.0)
        confidence = max(0.10, round(1.0 / (1.0 + phon_dist * 0.8), 2))

        # Generate reason
        reason = generate_suggestion_reason(query_word, word, phon_dist)

        scored.append({
            "word": word,
            "distance": dist,
            "weighted_distance": round(phon_dist, 2),
            "confidence": confidence,
            "score": round(composite_score, 4),
            "reason": reason,
        })

    # Sort primarily by composite score, then by distance, then alphabetically
    scored.sort(key=lambda x: (x["score"], x["distance"], x["word"]))

    # Deduplicate while preserving order
    seen = set()
    unique_ranked = []
    for item in scored:
        if item["word"] not in seen:
            seen.add(item["word"])
            unique_ranked.append(item)
        if len(unique_ranked) >= max_results:
            break

    return unique_ranked

