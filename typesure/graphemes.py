"""
typesure/graphemes.py — Tamil Grapheme Cluster Segmentation.

In the Tamil script, orthographic syllables (அட்சரம் / graphemes) consist of:
  1. Standalone vowels (உயிர்): U+0B85..U+0B94
  2. Standalone consonants / Grantha: U+0B95..U+0BAA, etc.
  3. Pure consonants with virama (மெய் / புள்ளி): Consonant + U+0BCD (்)
  4. Combined vowel-consonants (உயிர்மெய்): Consonant + Vowel sign (ா, ி, ீ, ு, ூ, ெ, ே, ை, ொ, ோ, ௌ)
  5. Aytham (ஆய்தம்): ஃ (U+0B83)
  6. Consonant + Virama + Zero-Width Joiner/Non-Joiner sequences.

Standard codepoint-based algorithms count "க்" as 2 characters and "கி" as 2 characters,
which distorts edit distance and character boundaries. Grapheme-aware segmentation
treats each orthographic syllable as a single discrete linguistic unit.
"""

import re
from typing import List

# Tamil Unicode blocks:
# Vowels (உயிர்): \u0B85-\u0B94
# Aytham (ஆய்தம்): \u0B83
# Consonants (மெய்): \u0B95-\u0BB9
# Virama / Pulli: \u0BCD
# Vowel signs (உயிர்மெய் குறிகள்): \u0BBE-\u0BCC, \u0BD7

# Grapheme regex pattern
_TAMIL_GRAPHEME_RE = re.compile(
    r'[\u0B95-\u0BB9\u0B83]'               # Consonant or Aytham
    r'(?:[\u0BCD]|[\u0BBE-\u0BCC\u0BD7])?' # Optional Virama or Vowel sign
    r'|[\u0B85-\u0B94]'                    # Independent vowel
    r'|[\u0B80-\u0BFF]'                    # Fallback single Tamil codepoint
    r'|[^\u0B80-\u0BFF]'                   # Non-Tamil single character
)


def split_graphemes(text: str) -> List[str]:
    """
    Segment a string into Tamil orthographic syllables (grapheme clusters).

    Examples:
      >>> split_graphemes("வணக்கம்")
      ['வ', 'ண', 'க்', 'க', 'ம்']
      >>> split_graphemes("தமிழ்")
      ['த', 'மி', 'ழ்']
      >>> split_graphemes("ஆசிரியர்")
      ['ஆ', 'சி', 'ரி', 'ய', 'ர்']
    """
    if not text:
        return []
    return _TAMIL_GRAPHEME_RE.findall(text)


def grapheme_length(text: str) -> int:
    """Return the number of Tamil grapheme clusters in text."""
    return len(split_graphemes(text))


def is_pure_consonant(grapheme: str) -> bool:
    """Check if the grapheme is a consonant with virama (மெய்யெழுத்து, e.g. க், ங்)."""
    return len(grapheme) == 2 and grapheme.endswith('\u0BCD')


def is_vowel_consonant(grapheme: str) -> bool:
    """Check if the grapheme is a consonant with a vowel sign (உயிர்மெய், e.g. கா, கி)."""
    return len(grapheme) == 2 and '\u0BBE' <= grapheme[1] <= '\u0BD7' and grapheme[1] != '\u0BCD'


def get_base_consonant(grapheme: str) -> str:
    """Return the base consonant codepoint if present, else the grapheme itself."""
    if len(grapheme) >= 1 and '\u0B95' <= grapheme[0] <= '\u0BB9':
        return grapheme[0]
    return grapheme

