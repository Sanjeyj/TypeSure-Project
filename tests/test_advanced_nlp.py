"""
tests/test_advanced_nlp.py — Comprehensive Unit & Integration Tests
for Advanced Tamil NLP, BK-Tree, Weighted Levenshtein, Morphology & Ranking.
"""

import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import pytest
from typesure.graphemes import split_graphemes, grapheme_length, is_pure_consonant, is_vowel_consonant
from typesure.weighted_levenshtein import weighted_levenshtein, grapheme_levenshtein, default_levenshtein
from typesure.bktree import BKTree
from typesure.morphology import check_morphological_inflection
from typesure.ranking import rank_candidates
from typesure.database import (
    save_custom_words,
    load_persisted_custom_words,
    delete_history_item,
    save_check,
    get_history
)


class TestTamilGraphemes:
    def test_basic_grapheme_split(self):
        # வணக்கம் -> வ, ண, க், க, ம் (5 orthographic syllables)
        g = split_graphemes("வணக்கம்")
        assert g == ["வ", "ண", "க்", "க", "ம்"]
        assert grapheme_length("வணக்கம்") == 5

    def test_pure_consonant_detection(self):
        assert is_pure_consonant("க்")
        assert is_pure_consonant("ம்")
        assert not is_pure_consonant("க")
        assert not is_pure_consonant("கா")

    def test_vowel_consonant_detection(self):
        assert is_vowel_consonant("கி")
        assert is_vowel_consonant("பூ")
        assert not is_vowel_consonant("க்")
        assert not is_vowel_consonant("அ")

    def test_empty_string(self):
        assert split_graphemes("") == []
        assert grapheme_length("") == 0


class TestWeightedLevenshtein:
    def test_exact_match(self):
        assert weighted_levenshtein("தமிழ்", "தமிழ்") == 0.0

    def test_nasal_confusion_penalty(self):
        # ண vs ன has lower substitution cost (0.55) than unrelated letters
        cost_confused = weighted_levenshtein("மணம்", "மனம்")
        cost_unrelated = weighted_levenshtein("மணம்", "மரம்")
        assert cost_confused < cost_unrelated

    def test_liquid_lateral_confusion_penalty(self):
        # ல vs ள vs ழ
        cost_lateral = weighted_levenshtein("பழம்", "பளம்")
        cost_unrelated = weighted_levenshtein("பழம்", "படம்")
        assert cost_lateral < cost_unrelated

    def test_grapheme_levenshtein(self):
        # வணக்கம் (5 graphemes) vs வணகம் (4 graphemes) -> distance 1 grapheme
        d = grapheme_levenshtein("வணக்கம்", "வணகம்")
        assert d == 1


class TestBKTree:
    def test_bktree_metric_axioms(self):
        tree = BKTree()
        words = ["வணக்கம்", "வணகம்", "வணங்கி", "நன்றி", "தமிழ்", "தமிழன்"]
        added = tree.build_from_iterable(words)
        assert added == len(words)
        assert tree.size == len(words)

    def test_bktree_search_exact_and_fuzzy(self):
        tree = BKTree()
        tree.add("வணக்கம்")
        tree.add("வணகம்")
        tree.add("தமிழ்")

        # In codepoint Levenshtein, வணக்கம் vs வணகம் is distance 2 (missing ் and க)
        results = tree.search("வணக்கம்", max_distance=2)
        found_words = [w for d, w in results]
        assert "வணக்கம்" in found_words
        assert "வணகம்" in found_words
        assert "தமிழ்" not in found_words

    def test_empty_tree_search(self):
        tree = BKTree()
        assert tree.search("வணக்கம்", max_distance=2) == []


class TestMorphologicalInflection:
    def test_plural_inflection(self):
        # Lemma: மாணவர், Inflected: மாணவர்கள்
        dict_mock = lambda w: w in {"மாணவர்", "படம்", "கல்லூரி", "தமிழ்"}
        res = check_morphological_inflection("மாணவர்கள்", dict_mock)
        assert res is not None
        assert res["is_valid_inflected"] is True
        assert res["lemma"] == "மாணவர்"
        assert res["category"] == "plural"

    def test_locative_case_inflection(self):
        # Lemma: கல்லூரி, Inflected: கல்லூரியில்
        dict_mock = lambda w: w in {"கல்லூரி"}
        res = check_morphological_inflection("கல்லூரியில்", dict_mock)
        assert res is not None
        assert res["lemma"] == "கல்லூரி"
        assert res["category"] == "locative"

    def test_accusative_case_inflection(self):
        # Lemma: தமிழ், Inflected: தமிழை
        dict_mock = lambda w: w in {"தமிழ்"}
        res = check_morphological_inflection("தமிழை", dict_mock)
        assert res is not None
        assert res["lemma"] == "தமிழ்"
        assert res["category"] == "accusative"

    def test_non_inflected_word(self):
        dict_mock = lambda w: w in {"வணக்கம்"}
        assert check_morphological_inflection("வணக்கம்", dict_mock) is None


class TestCandidateRanking:
    def test_ranking_prefers_phonologically_closer_words(self):
        query = "மணம்"
        candidates = [
            {"word": "மரம்", "distance": 1},
            {"word": "மனம்", "distance": 1},  # ண vs ன confusion
        ]
        ranked = rank_candidates(query, candidates, max_results=2)
        assert len(ranked) == 2
        # 'மனம்' should be ranked before 'மரம்' due to lower phonological cost
        assert ranked[0]["word"] == "மனம்"
        assert "confidence" in ranked[0]
        assert ranked[0]["confidence"] > 0


class TestDatabaseAndHistoryIsolation:
    def test_custom_words_persistence(self):
        test_words = ["செயற்கைக்கோள்", "தானியங்கி"]
        saved = save_custom_words(test_words)
        assert saved >= 1
        loaded = load_persisted_custom_words()
        assert "செயற்கைக்கோள்" in loaded

    def test_delete_history_item(self):
        check_id = save_check(
            word_count=5,
            issue_count=1,
            corrections=0,
            session_id="test_session_xyz"
        )
        assert check_id > 0

        # Delete single item
        deleted = delete_history_item(check_id, session_id="test_session_xyz")
        assert deleted is True

        # Ensure it no longer exists
        history = get_history(limit=10, session_id="test_session_xyz")
        ids = [h["id"] for h in history]
        assert check_id not in ids
