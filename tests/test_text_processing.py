"""
test_text_processing.py — Additional focused tests for text_processing module.
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import pytest
from typesure.text_processing import tokenize, normalize, count_words, extract_words


class TestExtractWords:
    def test_basic(self):
        words = extract_words("வணக்கம் நன்றி")
        assert "வணக்கம்" in words
        assert "நன்றி" in words

    def test_ignores_punctuation(self):
        words = extract_words("வணக்கம், நன்றி!")
        assert "," not in words
        assert "!" not in words

    def test_ignores_english(self):
        words = extract_words("Hello வணக்கம் world")
        # extract_words only returns Tamil-regex matches
        for w in words:
            assert any("\u0B80" <= c <= "\u0BFF" for c in w)

    def test_empty(self):
        assert extract_words("") == []

    def test_repeated(self):
        words = extract_words("வணக்கம் வணக்கம்")
        assert len(words) == 2


class TestCountWordsEdgeCases:
    def test_only_numbers(self):
        r = count_words("123 456 789")
        assert r["total_words"] == 0

    def test_only_punctuation(self):
        r = count_words("... !!! ???")
        assert r["total_words"] == 0

    def test_character_count_no_spaces(self):
        r = count_words("வணக்கம்")
        # "வணக்கம்" has 7 characters
        assert r["characters"] == 7

    def test_tabs_and_newlines(self):
        r = count_words("வணக்கம்\t\nநன்றி")
        assert r["tamil_words"] == 2


class TestNormalizeEdgeCases:
    def test_long_text_normalize(self):
        text = "வணக்கம் " * 1000
        result = normalize(text)
        assert len(result) > 0

    def test_control_characters_pass_through(self):
        text = "வணக்கம்\x00நன்றி"
        result = normalize(text)
        # NFC normalization passes through control chars
        assert "\x00" in result
