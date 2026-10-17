"""
text_processing.py — Tamil Unicode text tokenization and normalization.

Tamil Unicode block: U+0B80–U+0BFF
This module provides utilities for:
  - Unicode NFC normalization of Tamil text.
  - Tokenization that preserves Tamil words and ignores punctuation tokens.
  - Detection of whether a token is a Tamil word.
  - Detection of whether a token is an English word (to skip checking).
"""

import re
import unicodedata


# Tamil Unicode range: 0B80–0BFF
_TAMIL_CHAR_RE = re.compile(r'[\u0B80-\u0BFF]')

# A "Tamil word" token: one or more Tamil Unicode characters, optionally with
# Western digits embedded (e.g. abbreviations). We do not include punctuation.
_TAMIL_TOKEN_RE = re.compile(r'[\u0B80-\u0BFF]+(?:[\u0B80-\u0BFF\d]*[\u0B80-\u0BFF]+)*|[\u0B80-\u0BFF]+')

# A "Latin / English word" token: ASCII letters only
_ENGLISH_TOKEN_RE = re.compile(r'^[A-Za-z]+$')

# Tokenize preserving both Tamil tokens and non-Tamil spans
_SPLIT_RE = re.compile(r'([\u0B80-\u0BFF]+|[A-Za-z]+|[0-9]+|[^\w\s]|\s+)')


def normalize(text: str) -> str:
    """
    Apply Unicode NFC normalization to text.

    NFC (Canonical Decomposition followed by Canonical Composition) is the
    recommended form for Tamil Unicode, ensuring that composed forms (e.g.
    vowel signs attached to consonants) are stored consistently.
    """
    if not isinstance(text, str):
        raise TypeError("normalize() expects a str, got %s" % type(text).__name__)
    return unicodedata.normalize("NFC", text)


def is_tamil_token(token: str) -> bool:
    """
    Return True if the token contains at least one Tamil Unicode character
    and consists only of Tamil Unicode characters (no Latin letters).

    This allows tokens like pure Tamil words. Mixed Tamil+Latin tokens
    (transliterations) are treated as non-Tamil to avoid false positives.
    """
    if not token:
        return False
    has_tamil = bool(_TAMIL_CHAR_RE.search(token))
    has_latin = bool(re.search(r'[A-Za-z]', token))
    return has_tamil and not has_latin


def is_english_token(token: str) -> bool:
    """Return True if the token looks like a plain English/Latin word."""
    return bool(_ENGLISH_TOKEN_RE.match(token))


def tokenize(text: str) -> list:
    """
    Split text into a list of span dictionaries.

    Each span dict has:
      - 'text'  : the literal string
      - 'start' : character offset in the original text
      - 'end'   : character offset (exclusive)
      - 'is_tamil' : bool — is this span a Tamil word?
      - 'is_english' : bool — is this span an English word?
      - 'is_word' : bool — is this a word (Tamil or English) vs punctuation/space?

    Preserving spans lets the frontend highlight the exact location of each
    suspected misspelling inside the original text.
    """
    text = normalize(text)
    spans = []
    pos = 0
    for m in _SPLIT_RE.finditer(text):
        token = m.group()
        start = m.start()
        end = m.end()
        tamil = is_tamil_token(token)
        english = is_english_token(token)
        word = tamil or english
        spans.append({
            "text": token,
            "start": start,
            "end": end,
            "is_tamil": tamil,
            "is_english": english,
            "is_word": word,
        })
        pos = end
    # If there is trailing text not matched (shouldn't happen), append it
    if pos < len(text):
        spans.append({
            "text": text[pos:],
            "start": pos,
            "end": len(text),
            "is_tamil": False,
            "is_english": False,
            "is_word": False,
        })
    return spans


def extract_words(text: str) -> list:
    """
    Return a list of Tamil word strings found in the text.

    Useful for simple word-count and dictionary-lookup tasks where span
    positions are not required.
    """
    text = normalize(text)
    return [m.group() for m in _TAMIL_TOKEN_RE.finditer(text)]


def count_words(text: str) -> dict:
    """
    Return a dict with:
      - 'total_words'   : total Tamil + English word tokens
      - 'tamil_words'   : number of Tamil word tokens
      - 'english_words' : number of English word tokens
      - 'characters'    : total character count (excluding whitespace)
    """
    spans = tokenize(text)
    tamil = sum(1 for s in spans if s["is_tamil"])
    english = sum(1 for s in spans if s["is_english"])
    chars = len(text.replace(" ", "").replace("\n", "").replace("\t", ""))
    return {
        "total_words": tamil + english,
        "tamil_words": tamil,
        "english_words": english,
        "characters": chars,
    }
