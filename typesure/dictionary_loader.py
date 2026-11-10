"""
typesure/dictionary_loader.py — Load, index, and manage the Tamil spelling dictionary.

Architecture:
-------------
1. O(1) exact membership testing using Python hash set.
2. Metric space indexing using a Burkhard-Keller (BK) Tree for sub-linear fuzzy retrieval.
3. Persistent custom dictionary storage via SQLite custom_words table.
4. Unicode NFC normalization on all entries upon insertion.
"""

import os
import unicodedata
from pathlib import Path
from typing import Set, List, Dict, Tuple, Optional
from .bktree import BKTree, default_levenshtein
from .database import save_custom_words, load_persisted_custom_words

# Path to the bundled starter dictionary
_DATA_DIR = Path(__file__).parent.parent / "data"
_STARTER_DICT_PATH = _DATA_DIR / "ta_dictionary.txt"

# Limits
MAX_IMPORT_SIZE_BYTES = 2 * 1024 * 1024
MAX_IMPORT_WORDS = 50_000


def _nfc(word: str) -> str:
    return unicodedata.normalize("NFC", word.strip())


class TamilDictionary:
    """
    Manages the Tamil spelling word list, BK-tree index, and custom persistence.
    """
    _bktree: Optional[BKTree] = None

    def __init__(self):
        self.words: Set[str] = set()
        self.starter_count: int = 0
        self.imported_count: int = 0
        self._bktree = BKTree(distance_fn=default_levenshtein)

        self._load_starter()
        self._load_persisted()

    @property
    def bktree(self) -> BKTree:
        if getattr(self, "_bktree", None) is None:
            self._bktree = BKTree(distance_fn=default_levenshtein)
            for w in getattr(self, "words", set()):
                self._bktree.add(w)
        return self._bktree

    @bktree.setter
    def bktree(self, val: BKTree):
        self._bktree = val

    # ------------------------------------------------------------------
    # Internal loaders
    # ------------------------------------------------------------------

    def _load_starter(self):
        """Load words from the bundled ta_dictionary.txt."""
        path = _STARTER_DICT_PATH
        if not path.is_file():
            return
        count = 0
        with open(path, encoding="utf-8") as fh:
            for raw in fh:
                word = _nfc(raw)
                if word and not word.startswith("#"):
                    if word not in self.words:
                        self.words.add(word)
                        self.bktree.add(word)
                        count += 1
        self.starter_count = count

    def _load_persisted(self):
        """Load any previously imported words stored in the SQLite database."""
        try:
            persisted = load_persisted_custom_words()
            for raw in persisted:
                word = _nfc(raw)
                if word and word not in self.words:
                    self.words.add(word)
                    self.bktree.add(word)
                    self.imported_count += 1
        except Exception:
            pass

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def contains(self, word: str) -> bool:
        """O(1) exact membership test."""
        return _nfc(word) in self.words

    def add_word(self, word: str, persist: bool = True) -> bool:
        """
        Add a single word to the dictionary and BK-tree.
        Optionally persists to SQLite.
        """
        w = _nfc(word)
        if not w or w in self.words:
            return False
        self.words.add(w)
        self.bktree.add(w)
        self.imported_count += 1
        if persist:
            try:
                save_custom_words([w])
            except Exception:
                pass
        return True

    def import_wordlist(self, text_content: str) -> dict:
        """
        Import words from a UTF-8 string (one word per line).
        Automatically validates, dedupes, updates BK-tree, and persists to DB.
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
        new_words: List[str] = []

        for i, raw in enumerate(lines, 1):
            word = _nfc(raw)
            if not word or word.startswith("#"):
                continue
            if len(word) > 60:
                invalid += 1
                if len(errors) < 10:
                    errors.append(f"Line {i}: word too long (>60 chars), skipped.")
                continue
            # Must contain at least one Tamil character
            if not any("\u0B80" <= ch <= "\u0BFF" for ch in word):
                invalid += 1
                if len(errors) < 10:
                    errors.append(f"Line {i}: '{word[:30]}' has no Tamil characters, skipped.")
                continue
            if word in self.words:
                duplicates += 1
            else:
                self.words.add(word)
                self.bktree.add(word)
                new_words.append(word)
                self.imported_count += 1
                added += 1

        if new_words:
            try:
                save_custom_words(new_words)
            except Exception:
                pass

        return {
            "added": added,
            "duplicates": duplicates,
            "invalid": invalid,
            "errors": errors,
        }

    def search_candidates_linear(self, word: str, max_dist: int = 2) -> List[Tuple[int, str]]:
        """Baseline length-filtered exhaustive candidate search."""
        wlen = len(word)
        results = []
        for dw in self.words:
            if abs(len(dw) - wlen) > max_dist:
                continue
            d = default_levenshtein(word, dw)
            if d <= max_dist:
                results.append((d, dw))
        return results

    def search_candidates_bktree(self, word: str, max_dist: int = 2) -> List[Tuple[int, str]]:
        """Sub-linear metric tree candidate search using BK-tree."""
        return self.bktree.search(word, max_distance=max_dist)

    def stats(self) -> dict:
        """Return dictionary statistics."""
        return {
            "total_words": len(self.words),
            "starter_words": self.starter_count,
            "imported_words": self.imported_count,
            "bktree_nodes": self.bktree.size,
        }


# Singleton instance
dictionary = TamilDictionary()
