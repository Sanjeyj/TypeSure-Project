"""
dictionary_loader.py — Load and manage the Tamil spelling dictionary.

The starter dictionary is a curated set of common Tamil words.
An additional external UTF-8 word list (one word per line) may be imported.

Design decisions:
  - Dictionary is stored as a Python set for O(1) lookup.
  - All words are NFC-normalized on load.
  - The module tracks the source of each word (starter vs imported).
  - Duplicate detection: importing a word already in the set is silently skipped.

Source note:
  The starter vocabulary included below was assembled manually for
  demonstration purposes. It does NOT claim full coverage of the Tamil lexicon.
  For production use, the Wiktionary Tamil word list or the OLTools Tamil
  dictionary (MIT/CC-licensed) should be used.
"""

import os
import unicodedata
from pathlib import Path


# Path to the bundled starter dictionary
_DATA_DIR = Path(__file__).parent.parent / "data"
_STARTER_DICT_PATH = _DATA_DIR / "ta_dictionary.txt"

# Maximum file size for imported dictionaries (2 MB)
MAX_IMPORT_SIZE_BYTES = 2 * 1024 * 1024

# Maximum number of words allowed in an import batch
MAX_IMPORT_WORDS = 50_000


def _nfc(word: str) -> str:
    return unicodedata.normalize("NFC", word.strip())


class TamilDictionary:
    """
    Manages the Tamil spelling word list used for spell-checking.

    Attributes:
        words (set): NFC-normalized Tamil words.
        starter_count (int): Words loaded from the bundled dictionary.
        imported_count (int): Words added via import.
    """

    def __init__(self):
        self.words: set = set()
        self.starter_count: int = 0
        self.imported_count: int = 0
        self._load_starter()

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _load_starter(self):
        """Load words from the bundled ta_dictionary.txt."""
        path = _STARTER_DICT_PATH
        if not path.is_file():
            # Graceful fallback — the app still runs with an empty dictionary.
            return
        count = 0
        with open(path, encoding="utf-8") as fh:
            for raw in fh:
                word = _nfc(raw)
                if word and not word.startswith("#"):
                    self.words.add(word)
                    count += 1
        self.starter_count = count

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def contains(self, word: str) -> bool:
        """Return True if the NFC-normalized word is in the dictionary."""
        return _nfc(word) in self.words

    def add_word(self, word: str) -> bool:
        """
        Add a single word to the in-memory dictionary.
        Returns True if it was new, False if it was already present.
        """
        w = _nfc(word)
        if not w:
            return False
        if w in self.words:
            return False
        self.words.add(w)
        return True

    def import_wordlist(self, text_content: str) -> dict:
        """
        Import words from a UTF-8 string (one word per line).

        Returns a dict:
          {
            "added":     int,   # new words added
            "duplicates": int,  # words already present
            "invalid":   int,   # lines rejected (too long, non-Tamil, etc.)
            "errors":    list,  # human-readable problem descriptions
          }
        """
        lines = text_content.splitlines()
        if len(lines) > MAX_IMPORT_WORDS:
            return {
                "added": 0,
                "duplicates": 0,
                "invalid": 0,
                "errors": [
                    f"File contains {len(lines)} lines which exceeds the "
                    f"limit of {MAX_IMPORT_WORDS}. Import rejected."
                ],
            }

        added = 0
        duplicates = 0
        invalid = 0
        errors = []

        for i, raw in enumerate(lines, 1):
            word = _nfc(raw)
            if not word or word.startswith("#"):
                continue  # blank line or comment
            if len(word) > 60:
                invalid += 1
                if len(errors) < 10:
                    errors.append(f"Line {i}: word too long (>60 chars), skipped.")
                continue
            # Must contain at least one Tamil character
            if not any("\u0B80" <= ch <= "\u0BFF" for ch in word):
                invalid += 1
                if len(errors) < 10:
                    errors.append(
                        f"Line {i}: '{word[:30]}' has no Tamil characters, skipped."
                    )
                continue
            if word in self.words:
                duplicates += 1
            else:
                self.words.add(word)
                self.imported_count += 1
                added += 1

        return {
            "added": added,
            "duplicates": duplicates,
            "invalid": invalid,
            "errors": errors,
        }

    def stats(self) -> dict:
        """Return a summary of the dictionary state."""
        return {
            "total_words": len(self.words),
            "starter_words": self.starter_count,
            "imported_words": self.imported_count,
        }


# Module-level singleton — shared across the Flask application.
dictionary = TamilDictionary()
