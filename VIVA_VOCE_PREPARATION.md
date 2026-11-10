# TypeSure — Final-Year Viva Voce Examination Guide

## B.Sc. Computer Science Final-Year Project
**Project Title**: Intelligent Tamil Spelling Detection and Correction System  
**Project Name**: TypeSure  

---

## 1. Project Abstract
**TypeSure** is a full-stack Tamil language technology application that detects spelling anomalies and generates linguistically ranked correction suggestions in Tamil Unicode script. Traditional spell-checkers tailored for European languages fail on Tamil due to its agglutinative morphology, complex Unicode diacritic representations, and phonological confusion patterns (such as retroflex vs. alveolar nasals and laterals). TypeSure introduces Unicode NFC normalization, orthographic grapheme cluster segmentation, a Burkhard-Keller (BK) metric tree for sub-linear candidate retrieval, a Tamil-aware phonological cost matrix, and morphological suffix stripping. The system is implemented as a lightweight Flask web application with a responsive, distraction-free editorial interface, session-isolated persistence, and zero third-party API exposure. Experimental evaluation over 52 benchmark test items demonstrated $100.00\%$ detection recall, $75.86\%$ precision, an F1-score of $86.27\%$, and a $1.42\times$ search speedup over linear scanning.

---

## 2. Project Presentation Framework

### 2.1 Problem Statement
1. **Unicode Disparity**: A single Tamil letter like **கி** or **க்** consists of multiple Unicode codepoints. Codepoint-level string distance distorts character boundaries and edit costs.
2. **Agglutinative Morphology**: Suffixation causes valid inflected words (e.g., `கல்லூரியில்`, `மாணவர்கள்`) to be falsely flagged as errors by standard dictionary lookups.
3. **Phonological Typing Errors**: Tamil typists routinely confuse nasals (`ண`/`ன`/`ந`), rhotics (`ர`/`ற`), laterals (`ல`/`ள`/`ழ`), and omit pulli marks. Standard Levenshtein treats these as arbitrary substitutions.
4. **Computational Inefficiency**: Exhaustive dictionary scanning scales poorly ($O(|V|)$ distance computations per typo).

### 2.2 Existing vs. Proposed System

| Dimension | Existing Academic Prototype | Proposed TypeSure System |
| :--- | :--- | :--- |
| **Character Handling** | Raw Unicode Codepoints | Grapheme Cluster Syllable Segmentation |
| **Search Structure** | Linear length-filtered iteration | Burkhard-Keller (BK) Metric Space Tree |
| **Distance Metric** | Unweighted Levenshtein ($O(1)$ uniform cost) | Tamil Phonological Weighted Levenshtein Matrix |
| **Morphology** | None (Lemmas only) | Sandhi-aware suffix stripper (Plurals, Cases) |
| **Candidate Ranking**| Simple integer distance + alphabetical tiebreak | Multi-factor objective (Phonological + Jaccard + Length) |
| **Privacy & Security**| Global shared SQLite history | Session-isolated history + Zero-leak default |
| **UI/UX** | Generic academic form | Editorial Indian Language Technology Design System |

---

## 3. Comprehensive Viva Voce Questions & Answers (25 Q&As)

### Q1: What is the primary objective of Project TypeSure?
**Answer**: TypeSure was developed to provide an explainable, accurate, and privacy-respecting Tamil spelling detection and correction engine that addresses Tamil-specific orthographic and morphological challenges using computational linguistics, metric space indexing, and modern web engineering.

### Q2: Why is Unicode NFC normalization necessary for Tamil text?
**Answer**: In Unicode, characters can be represented in composite (NFC) or decomposed (NFD) formats. For instance, a base consonant followed by a vowel sign can exist as two separate codepoints or a single precomposed representation depending on the input method or OS. Without NFC normalization, visually identical Tamil words would fail exact equality checks (`s1 == s2`) and produce distorted edit distances.

### Q3: What is an orthographic grapheme cluster in Tamil?
**Answer**: In Tamil, an orthographic syllable (அட்சரம்) consists of a base consonant and its dependent diacritics (e.g., `க்` = consonant + pulli virama; `கோ` = consonant + composite vowel sign). Standard string operations measure length in Unicode codepoints, counting `க்` as 2 characters. Grapheme segmentation groups these into single linguistic units so that adding or removing a virama is correctly recognized as an atomic edit.

### Q4: Explain the mathematical properties of the Levenshtein distance.
**Answer**: Levenshtein distance is a metric on strings that measures the minimum number of single-character insertions, deletions, and substitutions required to transform string $s_1$ into $s_2$. It satisfies four metric axioms:
1. Non-negativity: $d(x, y) \ge 0$
2. Identity: $d(x, y) = 0 \iff x = y$
3. Symmetry: $d(x, y) = d(y, x)$
4. Triangle Inequality: $d(x, z) \le d(x, y) + d(y, z)$

### Q5: How does a Burkhard-Keller (BK) Tree improve search performance?
**Answer**: A BK-Tree indexes dictionary words into an $n$-ary metric tree where edge weights represent discrete Levenshtein distances. When searching for candidates within radius $N$ of query $q$, the triangle inequality guarantees that for node $u$ with distance $d = \text{dist}(q, u)$, any matching candidate $v$ must satisfy edge weight $k \in [d - N, d + N]$. Branches outside this range are pruned without computing distances, achieving sub-linear query time.

### Q6: What is the time and space complexity of the Levenshtein algorithm in TypeSure?
**Answer**: Using the Wagner–Fischer dynamic programming algorithm with two-row optimization, the time complexity is $O(m \cdot n)$ where $m$ and $n$ are string lengths. The space complexity is optimized to $O(\min(m, n))$ by keeping only the previous and current rows in memory rather than a full $(m+1) \times (n+1)$ matrix.

### Q7: What are the primary Tamil phonological confusion classes modeled in your weighted matrix?
**Answer**: TypeSure models four primary confusion axes based on Tamil linguistics:
1. **Nasals**: `ண` (retroflex), `ன` (alveolar), and `ந` (dental).
2. **Rhotics**: `ர` (alveolar flap) and `ற` (alveolar trill).
3. **Laterals & Approximant**: `ல` (alveolar lateral), `ள` (retroflex lateral), and `ழ` (retroflex central approximant).
4. **Vowel Sign Lengths**: Short vs. long pairs (`ி`/`ீ`, `ு`/`ூ`, `ெ`/`ே`, `ொ`/`ோ`).
Substitutions within these classes receive a discounted cost of $0.55$ instead of $1.0$.

### Q8: How does TypeSure handle missing pulli (virama) marks?
**Answer**: Missing pulli marks are the most common Tamil typing mistake (e.g., typing `வணககம்` instead of `வணக்கம்`). TypeSure detects when the base consonant is identical and only the virama mark is missing, assigning a discounted transition penalty of $0.50$, which elevates the correct word to the top of the suggestion ranking.

### Q9: Why is morphological analysis crucial for Dravidian languages like Tamil?
**Answer**: Tamil is agglutinative, meaning words are formed by chaining suffixes to nominal and verbal roots. A dictionary containing only root words like `கல்லூரி` would falsely flag `கல்லூரியில்` (in college) as an error. Morphological suffix stripping separates the stem from case and plural suffixes, checking the root against the lexicon and eliminating false positives.

### Q10: How does TypeSure handle Tamil sandhi (புணர்ச்சி) mutations during stemming?
**Answer**: When Tamil suffixes attach to roots, sandhi rules alter the junction (e.g., `படம்` + `கள்` $\to$ `படங்கள்`; `வீடு` + `இல்` $\to$ `வீட்டில்`). The morphological engine inverts these transformations by mapping mutated suffix sequences back to their base consonants (e.g., `-ங்களில்` $\to$ `-ம்`; `-ட்டில்` $\to$ `-டு`).

### Q11: How are suggestions ranked when multiple candidates have the same edit distance?
**Answer**: TypeSure uses a multi-factor scoring function:
$$\text{Score} = 0.45 \cdot (\text{Levenshtein} / 3) + 0.30 \cdot (\text{WeightedPhonological} / 3) + 0.15 \cdot \text{JaccardGraphemeDistance} + 0.10 \cdot \text{LengthRatio}$$
Candidates with lower composite penalty scores are ranked highest.

### Q12: How is the confidence score calculated, and why is it not arbitrary?
**Answer**: Rather than fabricating artificial percentages, TypeSure computes a mathematically calibrated confidence score using logistic decay over the phonological weighted distance:
$$\text{Confidence} = \max\left(0.10, \; \text{round}\left(\frac{1}{1 + 0.8 \cdot d_{\text{phon}}}, \; 2\right)\right)$$
This yields a bounded value between $0.10$ and $1.00$ that decreases monotonically with distance.

### Q13: What database is used, and how is session isolation achieved?
**Answer**: SQLite3 with Write-Ahead Logging (WAL) is used for persistence. Multi-user session isolation is achieved by associating every check record with a `session_id` extracted from the client's `X-Session-ID` header or signed cookie. All SQL queries filter with `WHERE session_id = ?`, preventing cross-user data leakage.

### Q14: How does TypeSure deploy onto serverless platforms like Vercel where the filesystem is read-only?
**Answer**: On Vercel, the application detects the `VERCEL` environment variable and dynamically directs the SQLite database path to `/tmp/typesure.db`, the only writable scratch volume on serverless containers.

### Q15: What security headers are implemented, and why?
**Answer**: Outbound responses include:
- `X-Frame-Options: SAMEORIGIN` (prevents clickjacking)
- `X-Content-Type-Options: nosniff` (prevents MIME-type sniffing)
- `Content-Security-Policy (CSP)`: Restricts script execution to `'self'` and styles to Google Fonts CDN.
- `Referrer-Policy: strict-origin-when-cross-origin`

### Q16: How does the dictionary import functionality prevent denial-of-service (DoS)?
**Answer**: The import endpoint (`/api/dictionary/import`) enforces strict constraints:
1. Maximum upload size of 2 MB (`MAX_IMPORT_SIZE_BYTES`).
2. Maximum 50,000 words per import batch.
3. Extension restriction (`.txt` only).
4. UTF-8 decode verification.
5. Rejection of lines exceeding 60 characters or lacking Tamil codepoints.

### Q17: What was the empirical performance of TypeSure on the evaluation benchmark?
**Answer**: Tested against the 52-item benchmark dataset:
- Detection Recall: $100.00\%$
- Detection Precision: $75.86\%$
- Detection F1-Score: $86.27\%$
- Top-1 Suggestion Accuracy: $77.27\%$
- Average BK-Tree Search Latency: $2.501\text{ ms}$ ($1.42\times$ faster than linear search).

### Q18: What is the difference between dictionary coverage and spelling accuracy?
**Answer**: Dictionary coverage is the percentage of input words found in the dictionary. It is not equivalent to spelling accuracy because valid words absent from a limited lexicon will reduce coverage without being actual spelling mistakes. TypeSure explicitly communicates this distinction in its UI analytics.

### Q19: What happens when English words or punctuation are entered?
**Answer**: The tokenizer separates text into spans using regular expressions. Non-Tamil spans (ASCII Latin letters, digits, whitespace, punctuation) are flagged with `is_tamil = False` and preserved verbatim. They are never sent through the Tamil spell-checking pipeline.

### Q20: What are the main design choices of the editorial UI redesign?
**Answer**: The interface uses a palette of Forest Green (`#153C32`), Sage Green (`#28745B`), Warm Ivory (`#F7F5EF`), and Muted Gold (`#D8B875`). It employs Inter for UI elements and Noto Sans Tamil for Tamil script, featuring distraction-free typography, accessible modal dialogs, and non-blocking toast notifications.

### Q21: What is the role of the aytham (ஃ) character in Tamil, and how is it handled?
**Answer**: The aytham (`\u0B83`) is a distinct letter in Tamil that is neither a vowel nor a consonant. It is treated as an independent grapheme cluster and included in Tamil token validation.

### Q22: Can TypeSure replace text automatically?
**Answer**: No. By design, TypeSure never automatically modifies user content. The user must review suggestions and explicitly click to accept or reject them, upholding user autonomy and editorial control.

### Q23: How are custom dictionary imports persisted?
**Answer**: When a user uploads a valid `.txt` word list, unique words are added to the in-memory set, inserted into the BK-Tree, and stored in the SQLite `custom_words` table so that they persist across application restarts.

### Q24: What automated testing strategies were implemented?
**Answer**: The project contains 112 pytest automated tests across 4 test modules:
1. `test_advanced_nlp.py`: Graphemes, weighted costs, BK-trees, morphology, and ranking.
2. `test_routes.py`: HTTP endpoints, error handling, reports, and import validation.
3. `test_spellchecker.py`: Baseline normalization, Levenshtein distance, and dictionary state.
4. `test_text_processing.py`: Tokenization, span offsets, and edge cases.

### Q25: What are the future enhancements for TypeSure?
**Answer**: Future scope includes:
1. Expanding the lexicon to 100,000+ words using the Tamil Wiktionary corpus.
2. Context-aware n-gram language modeling for phonetic homophone disambiguation.
3. Integration of deep-learning sequence-to-sequence models (e.g., IndicBART) for sentence-level grammar correction.
4. Packaging as a cross-platform browser extension.
