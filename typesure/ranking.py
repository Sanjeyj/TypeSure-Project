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
from .graphemes import split_graphemes
from .weighted_levenshtein import weighted_levenshtein


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
    max_results: int = 5,
) -> List[Dict[str, Any]]:
    """
    Rank suggestion candidates using weighted multi-factor scoring.

    Parameters:
    -----------
    query_word : str
        The misspelled input word.
    candidates : list of dicts
        Each candidate has {"word": str, "distance": int} (or float).
    max_results : int
        Maximum number of suggestions to return.

    Returns:
    --------
    List of ranked candidate dicts with 'word', 'distance', 'confidence', 'score'.
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
        # Weights: 0.45 * raw distance + 0.30 * phonological + 0.15 * grapheme overlap + 0.10 * length diff
        composite_score = (
            0.45 * (dist / 3.0) +
            0.30 * (phon_dist / 3.0) +
            0.15 * g_dist +
            0.10 * len_diff
        )

        # Calculate a calibrated confidence score (0.0 to 1.0)
        # Confidence decays exponentially with distance
        confidence = max(0.10, round(1.0 / (1.0 + phon_dist * 0.8), 2))

        scored.append({
            "word": word,
            "distance": dist,
            "weighted_distance": phon_dist,
            "confidence": confidence,
            "score": round(composite_score, 4),
        })

    # Sort primarily by composite score, then by word
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

