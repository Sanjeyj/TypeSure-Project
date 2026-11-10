# TypeSure — Mathematical & Algorithmic Documentation

This document formalizes the natural language processing, discrete metric search, and dynamic programming algorithms implemented in **TypeSure**.

---

## 1. Unicode NFC Normalization

### Problem
In the Unicode standard, Tamil text can be encoded in decomposed canonical sequences (NFD) or precomposed composite characters (NFC). For example, the syllable **கி** can be stored as:
1. Decomposed: `U+0B95` (`க`) + `U+0BC0` (`ி`)
2. Inconsistent ordering of vowel signs and pulli virama across different operating system keyboards.

### Solution
TypeSure enforces Unicode Canonical Composition (NFC):
$$\text{NFC}(T) = \mathcal{C}(\mathcal{D}(T))$$
Where $\mathcal{D}$ decomposes characters into canonical base elements, and $\mathcal{C}$ composes them into unique canonical representations. This ensures consistent byte representation before set membership and edit-distance evaluation.

---

## 2. Tamil Grapheme Syllable Segmentation

Standard ASCII-centric tokenizers treat individual Unicode codepoints as letters. In Tamil:
- `க்` consists of $2$ codepoints: `\u0B95` + `\u0BCD`
- `கோ` consists of $2$ codepoints: `\u0B95` + `\u0BCA`

Codepoint-based edit distance assigns a cost of $2$ to transform `க` into `கோ`, whereas linguistically this is a single grapheme substitution.

### Grapheme Extraction Rule
$$\text{Grapheme} = \begin{cases}
C + V_{\text{sign}} & \text{Consonant with dependent vowel sign} \\
C + \text{Virama} & \text{Pure consonant with pulli} \\
V_{\text{indep}} & \text{Standalone vowel} \\
\text{Aytham} & \text{U+0B83 (\u0B83)}
\end{cases}$$

The regular expression segmentation matches:
$$[\text{U+0B95–U+0BB9, U+0B83}](?:[\text{U+0BCD}] \mid [\text{U+0BBE–U+0BCC, U+0BD7}])? \mid [\text{U+0B85–U+0B94}]$$

---

## 3. Levenshtein Edit Distance (Wagner–Fischer Algorithm)

The standard Levenshtein distance $d_{\text{edit}}(s_1, s_2)$ between two strings $s_1$ (length $m$) and $s_2$ (length $n$) is computed via dynamic programming:

$$D(i, j) = \begin{cases}
i & \text{if } j = 0 \\
j & \text{if } i = 0 \\
D(i-1, j-1) & \text{if } s_1[i] = s_2[j] \\
1 + \min \begin{cases} D(i-1, j) & \text{(Deletion)} \\ D(i, j-1) & \text{(Insertion)} \\ D(i-1, j-1) & \text{(Substitution)} \end{cases} & \text{otherwise}
\end{cases}$$

### Memory Optimization
Instead of maintaining an $m \times n$ matrix, TypeSure maintains two rows ($\text{prev}$ and $\text{curr}$), reducing spatial complexity from $O(m \cdot n)$ to $O(\min(m, n))$.

---

## 4. Tamil-Aware Weighted Phonological Distance

Not all typos are equal. In Tamil orthography, certain letters are frequently substituted due to phonological proximity:

### 1. Nasal Confusion Group
$$\mathcal{N} = \{\text{ண (retroflex)}, \text{ன (alveolar)}, \text{ந (dental)}\}$$
Substitution cost:
$$\text{Cost}(c_1, c_2) = 0.55 \quad \forall \; c_1, c_2 \in \mathcal{N}, \; c_1 \neq c_2$$

### 2. Liquid & Approximant Group
$$\mathcal{L} = \{\text{ல (alveolar lateral)}, \text{ள (retroflex lateral)}, \text{ழ (retroflex approximant)}\}$$
Substitution cost:
$$\text{Cost}(c_1, c_2) = 0.55 \quad \forall \; c_1, c_2 \in \mathcal{L}, \; c_1 \neq c_2$$

### 3. Rhotic Confusion Group
$$\mathcal{R} = \{\text{ர (alveolar flap)}, \text{ற (alveolar trill)}\}$$
Substitution cost:
$$\text{Cost}(c_1, c_2) = 0.55 \quad \forall \; c_1, c_2 \in \mathcal{R}, \; c_1 \neq c_2$$

### 4. Virama Omission / Insertion
When the base consonant is identical and only the virama pulli mark is missing (e.g., `க` vs `க்`):
$$\text{Cost}(\text{Grapheme}_1, \text{Grapheme}_2) = 0.50$$

---

## 5. Burkhard-Keller (BK) Metric Tree Search

### Metric Axioms
A function $d: X \times X \to \mathbb{R}$ is a metric if and only if:
1. $d(x, y) \ge 0$ (Non-negativity)
2. $d(x, y) = 0 \iff x = y$ (Identity of indiscernibles)
3. $d(x, y) = d(y, x)$ (Symmetry)
4. $d(x, z) \le d(x, y) + d(y, z)$ (Triangle Inequality)

Because Levenshtein distance satisfies all four axioms, discrete metric tree indexing is mathematically sound.

### Pruning Criterion
Let $u$ be the current node in the BK-tree, $q$ be the query word, and $N$ be the maximum search radius ($N = 2$).
For any descendant $v$ stored under an edge of weight $k = d(u, v)$:
From the triangle inequality:
$$d(q, u) - d(u, v) \le d(q, v) \le d(q, u) + d(u, v)$$
$$d(q, u) - k \le d(q, v) \le d(q, u) + k$$

To satisfy $d(q, v) \le N$, we must have:
$$k \ge d(q, u) - N \quad \text{and} \quad k \le d(q, u) + N$$
$$\implies k \in [d(q, u) - N, \; d(q, u) + N]$$

Any sub-tree whose edge weight $k$ lies outside this closed interval is skipped without computing any distance metrics.

---

## 6. Morphological Suffix Analysis (Sandhi Decomposition)

Tamil nominals inflect via suffixation. When suffix $S$ is stripped, sandhi euphonic mutations must be inverted to identify root lemma $R$:

| Category | Suffix Pattern | Stem Mutation | Example Transformation |
| :--- | :--- | :--- | :--- |
| **Plural** | `-ங்கள்` | Replace with `-ம்` | படங்கள் $\to$ படம் |
| **Plural** | `-கள்` | Strip `-கள்` | மாணவர்கள் $\to$ மாணவர் |
| **Locative** | `-த்தில்` | Replace with `-ம்` | படத்தில் $\to$ படம் |
| **Locative** | `-ட்டில்` | Replace with `-டு` | வீட்டில் $\to$ வீடு |
| **Locative** | `-யில்` | Strip `-யில்` | கல்லூரியில் $\to$ கல்லூரி |
| **Accusative** | `-த்தை` | Replace with `-ம்` | மரத்தை $\to$ மரம் |
| **Accusative** | `-ட்டை` | Replace with `-டு` | வீட்டை $\to$ வீடு |
| **Accusative** | `-\u0BC8` (ை) | Replace with `-\u0BCD` (்) | தமிழை $\to$ தமிழ் |
| **Dative** | `-க்கு` / `-வுக்கு` | Strip suffix | கல்லூரிக்கு $\to$ கல்லூரி |
| **Genitive** | `-உடைய` | Strip suffix | என்னுடைய $\to$ என் |

---

## 7. Multi-Factor Candidate Ranking & Confidence

Candidates retrieved by the BK-tree are sorted using the multi-factor objective:
$$\text{Score}(q, c) = 0.45 \cdot \frac{d_{\text{edit}}(q, c)}{3} + 0.30 \cdot \frac{d_{\text{phon}}(q, c)}{3} + 0.15 \cdot d_{\text{Jaccard}}(q, c) + 0.10 \cdot \frac{|\text{len}(q) - \text{len}(c)|}{\max(\text{len}(q), \text{len}(c))}$$

Where grapheme Jaccard distance is:
$$d_{\text{Jaccard}}(q, c) = 1.0 - \frac{|G(q) \cap G(c)|}{|G(q) \cup G(c)|}$$

### Calibrated Confidence Score
A calibrated confidence measure (between $0.10$ and $1.00$) is derived via logistic decay over the phonological weighted distance:
$$\text{Confidence}(q, c) = \max\left(0.10, \; \text{round}\left(\frac{1}{1 + 0.8 \cdot d_{\text{phon}}(q, c)}, \; 2\right)\right)$$
This gives transparent, mathematically bounded confidence values without fabricating percentages.

