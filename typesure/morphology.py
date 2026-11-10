"""
typesure/morphology.py — Basic Tamil Morphological Analysis & Suffix Stripping.

Linguistic Background:
-----------------------
Tamil is a highly agglutinative Dravidian language where nominal stems take
multiple suffixes for number (plural), case (வேற்றுமை), and postpositional particles.
In an un-stemmed dictionary, valid inflections like "கல்லூரியில்" (in college),
"மாணவர்கள்" (students), or "தமிழை" (Tamil - accusative) are frequently flagged
as false-positive spelling errors if only root forms are stored.

This module implements rule-based morphological decomposition:
  1. Plural suffix detection: -கள், -க்கள்
  2. Case markers (வேற்றுமை உருபுகள்):
     - 2nd (Accusative): -ஐ
     - 3rd (Instrumental/Sociative): -ஆல், -உடன்
     - 4th (Dative): -க்கு, -வுக்கு, -ுக்கு
     - 5th (Ablative): -இலிருந்து, -இருந்து
     - 6th (Genitive): -இன், -உடைய
     - 7th (Locative): -இல், -இடம், -கண்
  3. Clitics & Conjunctions: -உம் (and/also), -ஆக (adverbializer), -ஆவது
"""

from typing import Optional, Dict, Callable, List, Tuple
from .text_processing import normalize

# Common Tamil nominal suffix definitions: (suffix, name, sandhi_substitutions)
# Note: In Tamil sandhi (புணர்ச்சி), attaching suffixes often mutates the stem:
# e.g. படம் + கள் -> படங்கள்; மரம் + ஐ -> மரத்தை; வீடு + இல் -> வீட்டில்.
SUFFIX_RULES: List[Tuple[str, str, List[Tuple[str, str]]]] = [
    # Complex suffixes first (longest match)
    ("-இலிருந்து", "ablative", [("இலிருந்து", "")]),
    ("-இருந்து",  "ablative", [("இருந்து", "")]),
    ("-உடைய",     "genitive", [("உடைய", "")]),
    ("-வுக்கு",    "dative",   [("வுக்கு", "")]),
    ("-க்கு",     "dative",   [("க்கு", "")]),
    ("-இடம்",     "locative", [("இடம்", "")]),
    ("-உடன்",     "sociative", [("உடன்", "")]),
    ("-க்கள்",    "plural",   [("க்கள்", "")]),
    ("-கள்",      "plural",   [
        ("ங்கள்", "ம்"),      # e.g. படங்கள் -> படம், புத்தகங்கள் -> புத்தகம்
        ("கள்", ""),          # e.g. மாணவர் + கள் -> மாணவர்கள்
    ]),
    ("-இல்",      "locative", [
        ("த்தில்", "ம்"),     # e.g. படத்தில் -> படம், மரத்தில் -> மரம்
        ("ட்டில்", "டு"),     # e.g. வீட்டில் -> வீடு
        ("யில்", ""),         # e.g. கல்லூரியில் -> கல்லூரி, பள்ளியில் -> பள்ளி
        ("இல்", "\u0BCD"),    # e.g. ஊரில் -> ஊர், தமிழில் -> தமிழ் (replaces ி+ல் with pulli)
        ("இல்", ""),
    ]),
    ("-ஆல்",      "instrumental", [
        ("த்தால்", "ம்"),     # e.g. படத்தால் -> படம்
        ("ட்டால்", "டு"),     # e.g. வீட்டால் -> வீடு
        ("யால்", ""),         # e.g. வழியால் -> வழி
        ("ஆல்", "\u0BCD"),
        ("ஆல்", ""),
    ]),
    ("-இன்",      "genitive", [
        ("த்தின்", "ம்"),     # e.g. படத்தின் -> படம்
        ("யின்", ""),
        ("இன்", "\u0BCD"),
        ("இன்", ""),
    ]),
    ("-ஐ",        "accusative", [
        ("த்தை", "ம்"),       # e.g. படத்தை -> படம், மரத்தை -> மரம்
        ("ட்டை", "டு"),       # e.g. வீட்டை -> வீடு
        ("யை", ""),           # e.g. மலையை -> மலை, தம்பியை -> தம்பி
        ("வை", ""),           # e.g. பறவையை -> பறவை
        ("\u0BC8", "\u0BCD"), # e.g. தமிழை -> தமிழ், அவனை -> அவன், நூலை -> நூல்
        ("ை", ""),
    ]),
    ("-ஆக",       "adverbial", [("ஆக", "")]),
    ("-உம்",      "conjunctive", [
        ("மும்", "ம்"),       # e.g. மரமும் -> மரம்
        ("யும்", ""),         # e.g. தம்பியும் -> தம்பி
        ("வும்", ""),         # e.g. பூவும் -> பூ
        ("உம்", ""),
    ]),
]


def check_morphological_inflection(
    word: str,
    dict_contains_fn: Callable[[str], bool],
) -> Optional[Dict]:
    """
    Check if `word` is a valid inflected form of a dictionary lemma.

    Parameters:
    -----------
    word : str
        Tamil word to check.
    dict_contains_fn : Callable[[str], bool]
        Function that returns True if a root/lemma exists in dictionary.

    Returns:
    --------
    dict with inflection details if recognized, else None.
    """
    word = normalize(word)
    if len(word) < 4:
        return None

    for suffix_tag, category, patterns in SUFFIX_RULES:
        for suffix_str, root_replacement in patterns:
            if word.endswith(suffix_str):
                stem = word[:-len(suffix_str)] + root_replacement
                stem = normalize(stem)
                if len(stem) >= 2 and dict_contains_fn(stem):
                    return {
                        "is_valid_inflected": True,
                        "lemma": stem,
                        "suffix": suffix_tag.lstrip("-"),
                        "category": category,
                        "original": word,
                    }

    return None
