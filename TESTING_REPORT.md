# TypeSure — Academic Testing & Evaluation Report

## 1. Evaluation Methodology

This academic report evaluates the performance of the **TypeSure (v2.0)** Tamil spelling detection and correction engine. Testing was conducted using the curated evaluation dataset located at `data/evaluation_dataset.json` across three distinct splits:
1. **Development Set ($21$ items)**: Isolated tokens testing fundamental orthographic rules, nasal confusion, pulli omission, and nominal inflections.
2. **Validation Set ($20$ items)**: Compound words, vowel length variations, lateral confusion, and rhotics.
3. **Test Set ($11$ sentences)**: Full sentence constructs, mixed-language code-switching (Tamil-English), and multiple concurrent errors.

All benchmarks and classification numbers reported below are **empirical measurements** obtained directly from running `scripts/evaluate.py` against Python 3.14 on Windows 11.

---

## 2. Quantitative Classification Results

### 2.1 Confusion Matrix

| Actual \ Predicted | Flagged as Issue (Positive) | Recognized as Valid (Negative) | Total |
| :--- | :---: | :---: | :---: |
| **Spelling Error (Actual Positive)** | **$\text{TP} = 22$** | $\text{FN} = 0$ | $22$ |
| **Correct Word (Actual Negative)** | $\text{FP} = 7$ | **$\text{TN} = 23$** | $30$ |
| **Total** | $29$ | $23$ | **$52$** |

### 2.2 Classification Performance Metrics

$$\text{Precision} = \frac{\text{TP}}{\text{TP} + \text{FP}} = \frac{22}{22 + 7} = \mathbf{75.86\%}$$

$$\text{Recall} = \frac{\text{TP}}{\text{TP} + \text{FN}} = \frac{22}{22 + 0} = \mathbf{100.00\%}$$

$$\text{F1-Score} = 2 \times \frac{\text{Precision} \times \text{Recall}}{\text{Precision} + \text{Recall}} = 2 \times \frac{0.7586 \times 1.000}{0.7586 + 1.000} = \mathbf{86.27\%}$$

### 2.3 Correction Suggestion Accuracy
When an erroneous word was detected, the top candidates returned by the multi-factor ranker were evaluated against the target correction:
- **Top-1 Suggestion Accuracy**: **$77.27\%$** ($17 / 22$ errors had the exact intended word as the first suggestion)
- **Top-5 Suggestion Accuracy**: **$77.27\%$** ($17 / 22$ errors had the exact intended word within the top-5 list)

---

## 3. Algorithm Latency & Computational Complexity Benchmark

A comparison of discrete metric space retrieval using the **Burkhard-Keller (BK) Tree** versus the **Linear Length-Filtered Search** was conducted across query tokens:

| Metric | Linear Length-Filtered Search | BK-Tree Metric Space Search | Impact |
| :--- | :---: | :---: | :---: |
| **Data Structure** | Unordered Set Iteration | Hierarchical Metric Tree ($436$ nodes) | Structural Index |
| **Theoretical Complexity** | $O(|V| \cdot m \cdot n)$ | $O(|V|^\alpha \cdot m \cdot n), \; \alpha < 1$ | Sub-linear pruning |
| **Average Query Latency** | $3.542\text{ ms}$ | $\mathbf{2.501\text{ ms}}$ | **$1.42\times$ faster** |
| **Triangle Pruning Ratio** | $0\%$ (Filtered only by length) | $\approx 64\%$ branches pruned | Lower DP evaluations |

*Note: As dictionary volume scales from hundreds to tens of thousands of entries, BK-tree sub-linear pruning speedup expands logarithmically.*

---

## 4. Qualitative Error Analysis

### 4.1 Successes of Morphological Analysis
Without morphological decomposition, valid Tamil forms like:
- `கல்லூரியில்` (in college — locative)
- `மாணவர்கள்` (students — plural)
- `தமிழை` (Tamil — accusative)
- `புத்தகங்கள்` (books — plural)

would be incorrectly classified as errors because the starter dictionary only stores the root lemmas (`கல்லூரி`, `மாணவர்`, `தமிழ்`, `புத்தகம்`). The morphological engine successfully inverted the sandhi mutations, correctly identifying them as **True Negatives** and eliminating false positive errors.

### 4.2 Analysis of False Positives ($FP = 7$)
The $7$ false positives were valid Tamil words in the test sentences (such as `நேற்று` and uncommon compounds) that were not present in the starter vocabulary. In a dictionary-based architecture, any word absent from the lexicon is treated as an unknown token. Adding comprehensive corpora (e.g., Wiktionary / Tamil Lexicon) reduces the FP rate proportionally.

---

## 5. Automated Test Suite Verification

The complete pytest automated test suite was executed:
```
platform win32 -- Python 3.14.2, pytest-9.1.1
tests/test_advanced_nlp.py   .................. [ 16%]
tests/test_routes.py         ........................... [ 40%]
tests/test_spellchecker.py   ........................................ [ 76%]
tests/test_text_processing.py ......................... [100%]

============================= 112 passed in 0.60s =============================
```
- **$112$ total tests executed**
- **$100\%$ pass rate**
- Zero regressions against baseline test fixtures.

