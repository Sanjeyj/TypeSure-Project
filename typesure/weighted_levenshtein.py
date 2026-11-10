"""
typesure/weighted_levenshtein.py — Tamil-Aware Phonological & Graphemic Edit Distance.

Mathematical Foundations:
-------------------------
Standard Levenshtein distance treats every substitution equally (cost = 1.0).
However, Tamil typographic and cognitive spelling mistakes systematically occur
along known linguistic confusion axes:
  1. Nasal confusion:      ண (retroflex) ↔ ன (alveolar) ↔ ந (dental)
  2. Rhotic confusion:     ர (medial flap) ↔ ற (alveolar trill)
  3. Liquid/Approximant:   ல (alveolar lateral) ↔ ள (retroflex lateral) ↔ ழ (retroflex central approximant)
  4. Vowel length pairs:   ி ↔ ீ, ு ↔ ூ, ெ ↔ ே, ொ ↔ ோ
  5. Virama/Pulli omission: consonant without virama ↔ consonant with virama (e.g. க ↔ க்)

This module computes:
  - Standard Levenshtein (baseline integer distance)
  - Tamil-Aware Weighted Levenshtein (float distance with phonological penalty matrix)
  - Grapheme-Aware Levenshtein (operating over orthographic syllables)
"""

from typing import List
from .graphemes import split_graphemes, get_base_consonant

# Confusion classes for base Tamil consonants
CONFUSION_GROUPS = [
    # 1. Nasals
    {"\u0BA3", "\u0BA9", "\u0BA8"},        # ண, ன, ந
    # 2. Rhotics
    {"\u0BA0", "\u0BB1"},                  # ர, ற (Note: \u0BB0 is ர, \u0BB1 is ற)
    {"\u0BB0", "\u0BB1"},                  # Corrected \u0BB0 (ர) and \u0BB1 (ற)
    # 3. Laterals & Approximant
    {"\u0BB2", "\u0BB3", "\u0BB4"},        # ல, ள, ழ
]

# Confusion pairs for vowel signs
VOWEL_SIGN_CONFUSIONS = [
    {"\u0BC0", "\u0BC1"},                  # ி (0BC0 in some decomposed forms) - standard: 0BBF (ி), 0BC0 (ீ)
    {"\u0BBF", "\u0BC0"},                  # ி, ீ
    {"\u0BC1", "\u0BC2"},                  # ு, ூ
    {"\u0BC6", "\u0BC7"},                  # ெ, ே
    {"\u0BCA", "\u0BCB"},                  # ொ, ோ
    {"\u0B85", "\u0B86"},                  # அ, ஆ
    {"\u0B87", "\u0B88"},                  # இ, ஈ
    {"\u0B89", "\u0B8A"},                  # உ, ஊ
    {"\u0B8E", "\u0B8F"},                  # எ, ஏ
    {"\u0B92", "\u0B93"},                  # ஒ, ஓ
]


def default_levenshtein(s1: str, s2: str) -> int:
    """Standard dynamic programming Levenshtein distance on characters."""
    if s1 == s2:
        return 0
    if not s1:
        return len(s2)
    if not s2:
        return len(s1)

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


def _substitution_cost_graphemes(g1: str, g2: str) -> float:
    """Calculate phonetic/orthographic substitution cost between two Tamil graphemes."""
    if g1 == g2:
        return 0.0

    # Check virama omission/addition on identical consonant (e.g. 'க' vs 'க்')
    b1 = get_base_consonant(g1)
    b2 = get_base_consonant(g2)

    if b1 == b2:
        # Same consonant base, one has virama/vowel sign variation
        return 0.5

    # Check if base consonants belong to a confusion group
    for group in CONFUSION_GROUPS:
        if b1 in group and b2 in group:
            # If they have identical vowel modifiers (e.g. ணி vs னி), cost is 0.55
            v1 = g1[1:] if len(g1) > 1 else ""
            v2 = g2[1:] if len(g2) > 1 else ""
            if v1 == v2:
                return 0.55
            return 0.75

    # Check standalone vowel confusions
    for group in VOWEL_SIGN_CONFUSIONS:
        if g1 in group and g2 in group:
            return 0.55

    return 1.0


def weighted_levenshtein(s1: str, s2: str) -> float:
    """
    Compute Tamil-aware weighted Levenshtein distance on grapheme clusters.
    Returns a float distance where linguistically close errors have lower cost.
    """
    g1 = split_graphemes(s1)
    g2 = split_graphemes(s2)

    n, m = len(g1), len(g2)
    if n == 0:
        return float(m)
    if m == 0:
        return float(n)

    # DP matrix optimization with two rows
    prev = [float(j) for j in range(m + 1)]
    curr = [0.0] * (m + 1)

    for i in range(1, n + 1):
        curr[0] = float(i)
        for j in range(1, m + 1):
            sub_cost = _substitution_cost_graphemes(g1[i - 1], g2[j - 1])
            curr[j] = min(
                prev[j] + 1.0,           # Deletion
                curr[j - 1] + 1.0,       # Insertion
                prev[j - 1] + sub_cost   # Substitution
            )
        prev, curr = curr, [0.0] * (m + 1)

    return round(prev[m], 3)


def grapheme_levenshtein(s1: str, s2: str) -> int:
    """
    Compute discrete Levenshtein edit distance on Tamil graphemes (integer distance).
    Treats each orthographic syllable as 1 unit.
    """
    g1 = split_graphemes(s1)
    g2 = split_graphemes(s2)

    n, m = len(g1), len(g2)
    if n == 0:
        return m
    if m == 0:
        return n

    prev = list(range(m + 1))
    for i in range(1, n + 1):
        curr = [i] + [0] * m
        for j in range(1, m + 1):
            cost = 0 if g1[i - 1] == g2[j - 1] else 1
            curr[j] = min(prev[j] + 1, curr[j - 1] + 1, prev[j - 1] + cost)
        prev = curr
    return prev[m]
