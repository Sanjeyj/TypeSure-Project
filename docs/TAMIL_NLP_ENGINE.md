# TypeSure — Tamil NLP Engine Technical Reference

## 1. Introduction & Linguistic Foundations

Tamil is an ancient, morphologically rich, highly agglutinative Dravidian language. Unlike Indo-European languages where words are often distinct roots with minor inflection, a single Tamil nominal or verbal lemma can generate hundreds of surface word forms through the systematic concatenation of bound morphemes.

Naïve dictionary lookups fail in Tamil because:
1. No static dictionary can enumerate every valid agglutinative word combination.
2. Character-level Levenshtein distance distorts Tamil orthography because dependent vowel signs (உயிர்மெய் குறிகள்) and viramas (புள்ளி) are separate Unicode codepoints.
3. Cognitive typing errors follow established phonological confusion axes rather than random character substitutions.

---

## 2. Grapheme Cluster Segmentation (`graphemes.py`)

A Tamil orthographic syllable (அட்சரம்) is treated as an indivisible linguistic unit:

| Syllable Type | Structure | Codepoints | Example | Grapheme Count | Standard Codepoint Count |
|---|---|---|---|:---:|:---:|
| Standalone Vowel (உயிர்) | V | `U+0B85` | அ | 1 | 1 |
| Pure Consonant (மெய்) | C + Virama | `U+0B95` + `U+0BCD` | க் | **1** | 2 |
| Vowel-Consonant (உயிர்மெய்) | C + Vowel Sign | `U+0B95` + `U+0BBE` | கா | **1** | 2 |
| Aytham (ஆய்தம்) | Independent | `U+0B83` | ஃ | 1 | 1 |
| Two-Part Vowel Sign | C + Left Sign + Right Sign | `U+0B95` + `U+0BCA` | கொ | **1** | 2 |

---

## 3. Agglutinative Morphology Engine (`morphology.py`)

TypeSure uses a rule-based suffix-stripping and sandhi-reconstruction pipeline:

```text
[ Input Token: "கல்லூரியில்" ]
             │
             ▼
[ Suffix Stripper detects "-இல்" (Locative Case Marker) ]
             │
             ▼
[ Sandhi Reverse Transform: "கல்லூரி" + "யில்" -> Root: "கல்லூரி" ]
             │
             ▼
[ Dictionary Lookup: Is "கல்லூரி" in Lexicon? -> YES ]
             │
             ▼
[ Recognition Status: VALID_MORPHOLOGICAL_FORM (Status: OK) ]
```

### Supported Morphological Classes:
1. **Plural Inflections**:
   - `-கள்`: e.g., `மாணவர்` + `கள்` -> `மாணவர்கள்`, `புத்தகம்` -> `புத்தகங்கள்` (`ம்` mutates to `ங்`).
   - `-க்கள்`: e.g., `பூ` + `க்கள்` -> `பூக்கள்`.
2. **Case Markers (வேற்றுமை உருபுகள்)**:
   - 2nd (Accusative `-ஐ`): `தமிழை` -> `தமிழ்`, `மரத்தை` -> `மரம்`, `வீட்டை` -> `வீடு`.
   - 3rd (Instrumental `-ஆல்`, Sociative `-உடன்`): `படத்தால்` -> `படம்`, `அவருடன்` -> `அவர்`.
   - 4th (Dative `-க்கு`, `-வுக்கு`): `கல்லூரிக்கு` -> `கல்லூரி`, `ஊருக்கு` -> `ஊர்`.
   - 5th (Ablative `-இலிருந்து`, `-இருந்து`): `வீட்டிலிருந்து` -> `வீடு`.
   - 6th (Genitive `-இன்`, `-உடைய`): `நாட்டின்` -> `நாடு`.
   - 7th (Locative `-இல்`, `-இடம்`): `பள்ளியில்` -> `பள்ளி`, `ஊரில்` -> `ஊர்`.
3. **Verbal Inflection Paradigms**:
   - Present tense markers: `-கிறு-`, `-க்கிறு-`, `-கின்று-`
   - Past tense markers: `-த்த-`, `-ந்த-`, `-ட்ட-`, `-ற்ற-`, `-இன்-`
   - Future tense markers: `-ப்-`, `-ப்ப-`, `-வ்-`
   - Negative and non-finite forms: `-வில்லை`, `-ஆமல்`, `-அ` (infinitive), `-உ/-இ` (participle).
