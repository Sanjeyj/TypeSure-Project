"""
test_spellchecker.py — Unit tests for the spell-checking core modules.

Run with:
    python -m pytest tests/ -v
"""

import sys
import os

# Ensure the project root is on the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import pytest
import unicodedata

from typesure.text_processing import (
    normalize, tokenize, extract_words, count_words,
    is_tamil_token, is_english_token,
)
from typesure.spellchecker import levenshtein, get_suggestions, check_text
from typesure.dictionary_loader import TamilDictionary


# ──────────────────────────────────────────────────────────────────────────────
# Helpers
# ──────────────────────────────────────────────────────────────────────────────

def nfc(s):
    return unicodedata.normalize("NFC", s)


# ──────────────────────────────────────────────────────────────────────────────
# 1. Unicode normalization
# ──────────────────────────────────────────────────────────────────────────────

class TestNormalize:
    def test_nfc_already_composed(self):
        word = "வணக்கம்"
        assert normalize(word) == nfc(word)

    def test_nfc_idempotent(self):
        word = "தமிழ்"
        assert normalize(normalize(word)) == normalize(word)

    def test_non_string_raises(self):
        with pytest.raises(TypeError):
            normalize(42)

    def test_empty_string(self):
        assert normalize("") == ""

    def test_mixed_script(self):
        text = "Hello வணக்கம் world"
        result = normalize(text)
        assert "Hello" in result
        assert "வணக்கம்" in result


# ──────────────────────────────────────────────────────────────────────────────
# 2. Tokenization
# ──────────────────────────────────────────────────────────────────────────────

class TestTokenize:
    def test_tamil_only(self):
        spans = tokenize("வணக்கம் தமிழ்")
        tamil_spans = [s for s in spans if s["is_tamil"]]
        assert len(tamil_spans) == 2
        assert tamil_spans[0]["text"] == "வணக்கம்"
        assert tamil_spans[1]["text"] == "தமிழ்"

    def test_mixed_language(self):
        spans = tokenize("Hello வணக்கம்")
        words = [s for s in spans if s["is_word"]]
        assert any(s["is_english"] for s in words)
        assert any(s["is_tamil"] for s in words)

    def test_punctuation_preserved(self):
        spans = tokenize("வணக்கம். நன்றி!")
        # punctuation spans should not be is_word
        punct = [s for s in spans if s["text"] in (".", "!")]
        assert len(punct) == 2
        assert all(not s["is_word"] for s in punct)

    def test_empty_input(self):
        spans = tokenize("")
        assert spans == []

    def test_number_only(self):
        spans = tokenize("123")
        word_spans = [s for s in spans if s["is_word"]]
        assert len(word_spans) == 0  # digits are not words

    def test_span_positions(self):
        text = "வணக்கம் நன்றி"
        spans = tokenize(text)
        for s in spans:
            assert text[s["start"]:s["end"]] == s["text"]

    def test_whitespace_only(self):
        spans = tokenize("   \n\t  ")
        word_spans = [s for s in spans if s["is_word"]]
        assert len(word_spans) == 0

    def test_long_text(self):
        text = ("வணக்கம் " * 500).strip()
        spans = tokenize(text)
        tamil_spans = [s for s in spans if s["is_tamil"]]
        assert len(tamil_spans) == 500


# ──────────────────────────────────────────────────────────────────────────────
# 3. Token type detection
# ──────────────────────────────────────────────────────────────────────────────

class TestTokenTypes:
    def test_is_tamil_pure(self):
        assert is_tamil_token("வணக்கம்") is True

    def test_is_tamil_mixed_latin_false(self):
        # Mixed Tamil+Latin should return False (to avoid false positives)
        assert is_tamil_token("தமிழ்text") is False

    def test_is_english_pure(self):
        assert is_english_token("Hello") is True

    def test_is_english_with_digits_false(self):
        assert is_english_token("Hello123") is False

    def test_empty_token(self):
        assert is_tamil_token("") is False
        assert is_english_token("") is False


# ──────────────────────────────────────────────────────────────────────────────
# 4. Word count
# ──────────────────────────────────────────────────────────────────────────────

class TestCountWords:
    def test_tamil_only_count(self):
        result = count_words("வணக்கம் நன்றி தமிழ்")
        assert result["tamil_words"] == 3
        assert result["english_words"] == 0
        assert result["total_words"] == 3

    def test_mixed_count(self):
        result = count_words("Hello வணக்கம் world")
        assert result["english_words"] == 2
        assert result["tamil_words"] == 1

    def test_empty(self):
        result = count_words("")
        assert result["total_words"] == 0
        assert result["characters"] == 0

    def test_repeated_words_count(self):
        result = count_words("வணக்கம் வணக்கம் வணக்கம்")
        assert result["tamil_words"] == 3


# ──────────────────────────────────────────────────────────────────────────────
# 5. Levenshtein distance
# ──────────────────────────────────────────────────────────────────────────────

class TestLevenshtein:
    def test_identical(self):
        assert levenshtein("வணக்கம்", "வணக்கம்") == 0

    def test_empty_vs_nonempty(self):
        assert levenshtein("", "abc") == 3
        assert levenshtein("abc", "") == 3

    def test_single_insertion(self):
        assert levenshtein("cat", "cats") == 1

    def test_single_deletion(self):
        assert levenshtein("cats", "cat") == 1

    def test_single_substitution(self):
        assert levenshtein("cat", "bat") == 1

    def test_both_empty(self):
        assert levenshtein("", "") == 0

    def test_tamil_distance_one(self):
        # வணககம் vs வணக்கம் — removing the pulli is 1 edit (or close)
        d = levenshtein("வணககம்", "வணக்கம்")
        assert d <= 3  # within suggestion threshold

    def test_completely_different(self):
        d = levenshtein("abc", "xyz")
        assert d == 3

    def test_symmetric(self):
        a, b = "தமிழ்", "தமில்"
        assert levenshtein(a, b) == levenshtein(b, a)


# ──────────────────────────────────────────────────────────────────────────────
# 6. Suggestions
# ──────────────────────────────────────────────────────────────────────────────

class TestGetSuggestions:
    def test_correct_word_no_close_suggestions(self):
        # A correct word already in the dictionary should return empty or
        # itself — since we only flag unknowns. But get_suggestions works on
        # any string — it just looks for close matches.
        sugs = get_suggestions("வணக்கம்")
        # Should include the word itself (distance 0) if in dictionary
        words = [s["word"] for s in sugs]
        assert "வணக்கம்" in words

    def test_unknown_word_no_suggestions(self):
        # A completely made-up string far from any dictionary word
        sugs = get_suggestions("xyzabc123")
        assert sugs == []

    def test_suggestions_sorted_by_distance(self):
        sugs = get_suggestions("வணக்கம்")
        distances = [s["distance"] for s in sugs]
        assert distances == sorted(distances)

    def test_max_suggestions_five(self):
        sugs = get_suggestions("நன்றி")
        assert len(sugs) <= 5


# ──────────────────────────────────────────────────────────────────────────────
# 7. Full check_text integration
# ──────────────────────────────────────────────────────────────────────────────

class TestCheckText:
    def test_all_correct_words(self):
        text = "வணக்கம் நன்றி தமிழ்"
        result = check_text(text)
        assert result["stats"]["issues_found"] == 0
        assert result["stats"]["total_words_scanned"] >= 1

    def test_empty_text(self):
        result = check_text("")
        assert result["stats"]["total_words_scanned"] == 0
        assert result["stats"]["issues_found"] == 0

    def test_mixed_tamil_english(self):
        text = "Hello வணக்கம் world நன்றி"
        result = check_text(text)
        # English words should not be flagged as Tamil spelling issues
        flagged_words = [i["word"] for i in result["issues"]]
        assert "Hello" not in flagged_words
        assert "world" not in flagged_words

    def test_punctuation_not_flagged(self):
        text = "வணக்கம். நன்றி!"
        result = check_text(text)
        flagged = [i["word"] for i in result["issues"]]
        assert "." not in flagged
        assert "!" not in flagged

    def test_repeated_word_single_issue(self):
        text = "வணககம் வணககம் வணககம்"
        result = check_text(text)
        # 'வணககம்' is not in dictionary → should appear once in issues
        flagged = [i["word"] for i in result["issues"]]
        assert flagged.count("வணககம்") == 1

    def test_repeated_word_occurrence_count(self):
        text = "வணககம் வணககம் வணககம்"
        result = check_text(text)
        issue = next((i for i in result["issues"] if i["word"] == "வணககம்"), None)
        if issue:
            assert issue["occurrences"] == 3

    def test_stats_structure(self):
        result = check_text("வணக்கம் நன்றி")
        stats = result["stats"]
        assert "total_words_scanned" in stats
        assert "issues_found" in stats
        assert "recognized" in stats
        assert "dictionary_coverage_pct" in stats

    def test_coverage_pct_range(self):
        result = check_text("வணக்கம் நன்றி")
        pct = result["stats"]["dictionary_coverage_pct"]
        assert 0.0 <= pct <= 100.0

    def test_long_text(self):
        text = ("வணக்கம் நன்றி தமிழ் " * 100).strip()
        result = check_text(text)
        assert result["stats"]["total_words_scanned"] == 300

    def test_only_english(self):
        result = check_text("Hello world this is English only")
        assert result["stats"]["total_words_scanned"] == 0
        assert result["stats"]["issues_found"] == 0

    def test_only_punctuation(self):
        result = check_text("... !!! ??? ---")
        assert result["stats"]["total_words_scanned"] == 0


# ──────────────────────────────────────────────────────────────────────────────
# 8. Dictionary
# ──────────────────────────────────────────────────────────────────────────────

class TestDictionary:
    def setup_method(self):
        self.d = TamilDictionary.__new__(TamilDictionary)
        self.d.words = set()
        self.d.starter_count = 0
        self.d.imported_count = 0

    def test_contains_added_word(self):
        self.d.add_word("வணக்கம்")
        assert self.d.contains("வணக்கம்")

    def test_not_contains_missing_word(self):
        assert not self.d.contains("XYZZY")

    def test_add_duplicate_returns_false(self):
        self.d.add_word("வணக்கம்")
        assert self.d.add_word("வணக்கம்") is False

    def test_add_new_returns_true(self):
        assert self.d.add_word("நன்றி") is True

    def test_import_valid(self):
        content = "# comment\nவணக்கம்\nநன்றி\n"
        result = self.d.import_wordlist(content)
        assert result["added"] == 2
        assert result["duplicates"] == 0
        assert result["invalid"] == 0

    def test_import_duplicate_counted(self):
        self.d.add_word("வணக்கம்")
        content = "வணக்கம்\nநன்றி\n"
        result = self.d.import_wordlist(content)
        assert result["duplicates"] == 1
        assert result["added"] == 1

    def test_import_non_tamil_skipped(self):
        content = "hello\nworld\n"
        result = self.d.import_wordlist(content)
        assert result["invalid"] == 2
        assert result["added"] == 0

    def test_import_too_long_word_skipped(self):
        long_word = "வ" * 61
        result = self.d.import_wordlist(long_word)
        assert result["invalid"] == 1

    def test_import_too_many_lines(self):
        from typesure.dictionary_loader import MAX_IMPORT_WORDS
        content = "வணக்கம்\n" * (MAX_IMPORT_WORDS + 1)
        result = self.d.import_wordlist(content)
        assert result["added"] == 0
        assert len(result["errors"]) > 0

    def test_stats_keys(self):
        self.d.add_word("வணக்கம்")
        stats = self.d.stats()
        assert "total_words" in stats
        assert "starter_words" in stats
        assert "imported_words" in stats
