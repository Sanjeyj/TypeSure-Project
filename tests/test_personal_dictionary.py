"""
tests/test_personal_dictionary.py — Unit & Integration tests for Personal Dictionary
and the 7-stage recognition pipeline in TypeSure.
"""

import pytest
from app import app
from typesure.database import (
    init_db,
    create_user,
    add_personal_word,
    get_personal_words,
    count_personal_words,
    update_personal_word,
    delete_personal_word,
    get_personal_word_set,
    import_personal_words,
)
from typesure.spellchecker import check_text, check_compound_word, get_suggestions
from typesure.ranking import generate_suggestion_reason, rank_candidates


@pytest.fixture(autouse=True)
def setup_db():
    init_db()


@pytest.fixture
def test_users():
    import uuid
    suffix = uuid.uuid4().hex[:6]
    u1_id = create_user(f"User One {suffix}", f"u1_{suffix}@example.com", "hash12345")
    u2_id = create_user(f"User Two {suffix}", f"u2_{suffix}@example.com", "hash67890")
    return u1_id, u2_id


class TestPersonalDictionaryCRUD:
    def test_add_and_retrieve_word(self, test_users):
        u1, _ = test_users
        word_id = add_personal_word(u1, "கனிமொழியன்", notes="Tamil proper name")
        assert word_id is not None

        words = get_personal_words(u1)
        found = [w for w in words if w["word"] == "கனிமொழியன்"]
        assert len(found) == 1
        assert found[0]["notes"] == "Tamil proper name"

    def test_duplicate_word_rejected(self, test_users):
        u1, _ = test_users
        w1 = add_personal_word(u1, "செயற்கைக்கோள்", notes="First")
        assert w1 is not None
        w2 = add_personal_word(u1, "செயற்கைக்கோள்", notes="Second")
        assert w2 is None

    def test_user_isolation(self, test_users):
        u1, u2 = test_users
        add_personal_word(u1, "தில்லி", notes="City of User 1")

        # User 1 has it
        u1_words = get_personal_word_set(u1)
        assert "தில்லி" in u1_words

        # User 2 does NOT have it
        u2_words = get_personal_word_set(u2)
        assert "தில்லி" not in u2_words

        # User 2 cannot delete User 1's word
        u1_list = get_personal_words(u1)
        target_id = u1_list[0]["id"]
        deleted = delete_personal_word(target_id, user_id=u2)
        assert not deleted

        # User 1 can delete it
        deleted_own = delete_personal_word(target_id, user_id=u1)
        assert deleted_own

    def test_update_notes(self, test_users):
        u1, _ = test_users
        wid = add_personal_word(u1, "நவீனத்துவம்", notes="Initial note")
        assert wid is not None
        ok = update_personal_word(wid, u1, "Updated literary terminology")
        assert ok
        words = get_personal_words(u1)
        assert any(w["notes"] == "Updated literary terminology" for w in words)

    def test_bulk_import(self, test_users):
        u1, _ = test_users
        words = ["வானூர்தி", "இயற்பியல்", "வானூர்தி"]  # contains a duplicate
        added, dups = import_personal_words(u1, words)
        assert added == 2
        assert dups == 1


class TestSevenStageRecognition:
    def test_verified_word(self):
        # வணக்கம் is in 12,500+ master dictionary
        res = check_text("வணக்கம்")
        assert res["spans"][0]["classification"] == "VERIFIED_WORD"
        assert res["spans"][0]["status"] == "ok"
        assert res["stats"]["issues_found"] == 0

    def test_morphological_inflection(self):
        # மாணவர்கள் = மாணவர் + கள்
        res = check_text("மாணவர்கள்")
        assert res["spans"][0]["classification"] in ("VALID_MORPHOLOGICAL_FORM", "VERIFIED_WORD")
        assert res["spans"][0]["status"] == "ok"

    def test_compound_word_recognition(self):
        # தமிழ்நாடு = தமிழ் + நாடு
        res = check_text("தமிழ்நாடு")
        assert res["spans"][0]["status"] == "ok"
        assert res["spans"][0]["classification"] in ("VALID_COMPOUND", "VERIFIED_WORD")

    def test_known_variant(self):
        # ஸ்ரீ honorific
        res = check_text("ஸ்ரீ")
        assert res["spans"][0]["status"] == "ok"
        assert res["spans"][0]["classification"] == "KNOWN_VARIANT"

    def test_personal_dictionary_recognition(self, test_users):
        u1, _ = test_users
        custom_term = "மின்கலனகம்"
        add_personal_word(u1, custom_term, notes="Technical term")

        # Without user_id, unrecognized
        res_guest = check_text(custom_term)
        assert res_guest["stats"]["issues_found"] == 1

        # With user_id, recognized as PERSONAL_DICTIONARY_WORD
        res_auth = check_text(custom_term, user_id=u1)
        assert res_auth["stats"]["issues_found"] == 0
        assert res_auth["spans"][0]["classification"] == "PERSONAL_DICTIONARY_WORD"
        assert res_auth["spans"][0]["status"] == "ok"

    def test_possible_spelling_error_vs_unknown(self):
        # "பளம்" is a phonological typo for "பழம்" (distance 1, ள vs ழ)
        res_typo = check_text("பளம்")
        assert len(res_typo["issues"]) == 1
        issue = res_typo["issues"][0]
        assert issue["classification"] == "POSSIBLE_SPELLING_ERROR"
        assert issue["message"] == "Possible spelling error"
        assert len(issue["suggestions"]) <= 3
        sug_words = [s["word"] for s in issue["suggestions"]]
        assert "பழம்" in sug_words


class TestLinguisticReasonGeneration:
    def test_lateral_confusion_reason(self):
        reason = generate_suggestion_reason("பளம்", "பழம்", 0.55)
        assert "லகர/ளகர/ழகர" in reason or "ள" in reason

    def test_nasal_confusion_reason(self):
        reason = generate_suggestion_reason("மனம்", "மணம்", 0.55)
        assert "ணகர/னகர" in reason or "ன" in reason

    def test_omission_reason(self):
        reason = generate_suggestion_reason("வணகம்", "வணக்கம்", 1.0)
        assert "விடுபடல்" in reason or "omission" in reason.lower()

    def test_max_three_suggestions_returned(self):
        ranked = rank_candidates("வணகம்", [
            {"word": "வணக்கம்", "distance": 1},
            {"word": "வணங்கு", "distance": 2},
            {"word": "வணங்க", "distance": 2},
            {"word": "வண்ணம்", "distance": 2},
        ], max_results=3)
        assert len(ranked) == 3
        for item in ranked:
            assert "reason" in item
            assert len(item["reason"]) > 0
