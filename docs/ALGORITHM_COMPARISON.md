# TypeSure — Algorithm Comparison & Mathematical Formulation

## 1. Metric Space Search: Linear vs. Burkhard-Keller Metric Tree

### Theoretical Formulations:
- **Exhaustive Linear Search**: Given a query token $q$ and a dictionary $D$ of size $|D|$, a linear search evaluates the distance function $d(q, w)$ for every $w \in D$, requiring:
  $$\text{Complexity: } O(|D| \cdot |q| \cdot |\bar{w}|)$$
- **Burkhard-Keller (BK) Tree**: Operates in a discrete metric space $(M, d)$ where $d$ satisfies:
  1. $d(x, y) \ge 0$ (Non-negativity)
  2. $d(x, y) = 0 \iff x = y$ (Identity)
  3. $d(x, y) = d(y, x)$ (Symmetry)
  4. $d(x, z) \le d(x, y) + d(y, z)$ (Triangle Inequality)

By the triangle inequality, for query $q$ and node $u$ with distance $d = d(q, u)$, any matching candidate $v$ within radius $N$ must satisfy:
$$d(u, v) \in [d - N, d + N]$$
Any subtree child whose edge weight falls outside this range is pruned without computing expensive string comparisons.

---

## 2. Empirical Benchmark Latencies

Measured across 1,972 dictionary lemmas:

| Algorithm | Average Search Latency | Complexity | Worst-Case Bound |
|---|:---:|:---:|:---:|
| **Linear Search** | 9.31 ms | $O(|D|)$ | Evaluates all 1,972 nodes |
| **BK-Tree Metric Tree** | **7.16 ms** | $O(N \log |D|)$ | Evaluates pruned subtrees (**1.30x speedup**) |

---

## 3. Multi-Factor Candidate Ranking Formulation

Given an unknown token $q$ and retrieved candidate set $C$, candidates are ranked by a composite penalty score:

$$\text{Score}(c, q) = w_{\text{dist}} \cdot \left(\frac{d(c, q)}{3.0}\right) + w_{\text{phon}} \cdot \left(\frac{d_{\text{phon}}(c, q)}{3.0}\right) + w_{\text{jac}} \cdot d_{\text{jaccard}}(c, q) + w_{\text{len}} \cdot \Delta_{\text{len}}(c, q)$$

### Weight Configuration:
- $w_{\text{dist}} = 0.45$: Integer edit distance bound.
- $w_{\text{phon}} = 0.30$: Phonological weighted cost matrix (penalizing nasals, rhotics, laterals).
- $w_{\text{jac}} = 0.15$: Grapheme Jaccard distance over orthographic syllable sets.
- $w_{\text{len}} = 0.10$: Length disparity ratio.

Candidates with the lowest composite score are ranked first.
