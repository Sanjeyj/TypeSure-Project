"""
typesure/bktree.py — Burkhard-Keller (BK) Metric Tree for Candidate Search.

Theoretical Background:
-----------------------
A BK-Tree is a specialized metric tree data structure defined for discrete
metric spaces (M, d) where d satisfies metric axioms:
  1. Non-negativity: d(x, y) >= 0
  2. Identity:       d(x, y) == 0 <=> x == y
  3. Symmetry:       d(x, y) == d(y, x)
  4. Triangle Ineq.: d(x, z) <= d(x, y) + d(y, z)

By the triangle inequality, for any query word q and tree node u with distance
d = dist(q, u), any candidate word v satisfying dist(q, v) <= N must have:
  dist(u, v) in [d - N, d + N]

Branches with edge weights outside this interval are safely pruned without
computing expensive string distances.
"""

from typing import List, Tuple, Dict, Optional, Callable


def default_levenshtein(s1: str, s2: str) -> int:
    """Standard dynamic programming Levenshtein distance."""
    if s1 == s2:
        return 0
    if not s1:
        return len(s2)
    if not s2:
        return len(s1)

    if len(s1) > len(s2):
        s1, s2 = s2, s1

    prev = list(range(len(s1) + 1))
    for ch2 in s2:
        curr = [prev[0] + 1]
        for j, ch1 in enumerate(s1):
            cost = 0 if ch1 == ch2 else 1
            curr.append(min(curr[j] + 1, prev[j + 1] + 1, prev[j] + cost))
        prev = curr
    return prev[-1]


class BKNode:
    """A single node in a BK-tree."""
    __slots__ = ("word", "children")

    def __init__(self, word: str):
        self.word: str = word
        self.children: Dict[int, BKNode] = {}


class BKTree:
    """
    Burkhard-Keller Tree implementation for fast sub-linear fuzzy string lookup.
    """

    def __init__(self, distance_fn: Optional[Callable[[str, str], int]] = None):
        self.root: Optional[BKNode] = None
        self.dist = distance_fn or default_levenshtein
        self.size: int = 0

    def add(self, word: str) -> bool:
        """Insert a word into the BK-tree. Returns True if inserted, False if duplicate."""
        if not word:
            return False

        if self.root is None:
            self.root = BKNode(word)
            self.size = 1
            return True

        curr = self.root
        while True:
            d = self.dist(curr.word, word)
            if d == 0:
                return False  # Already present

            if d in curr.children:
                curr = curr.children[d]
            else:
                curr.children[d] = BKNode(word)
                self.size += 1
                return True

    def build_from_iterable(self, words) -> int:
        """Populate tree with words from any iterable. Returns count of words added."""
        count = 0
        for w in words:
            if self.add(w):
                count += 1
        return count

    def search(self, query: str, max_distance: int = 2) -> List[Tuple[int, str]]:
        """
        Search for all words within `max_distance` of `query`.
        Returns a list of (distance, word) tuples.
        """
        if self.root is None or not query:
            return []

        results: List[Tuple[int, str]] = []
        candidates = [self.root]

        while candidates:
            node = candidates.pop()
            d = self.dist(query, node.word)

            if d <= max_distance:
                results.append((d, node.word))

            # Triangle inequality pruning:
            # child distance must fall in [d - max_distance, d + max_distance]
            low = d - max_distance
            high = d + max_distance

            for dist_k, child_node in node.children.items():
                if low <= dist_k <= high:
                    candidates.append(child_node)

        return results

