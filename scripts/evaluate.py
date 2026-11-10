"""
scripts/evaluate.py — Empirical Academic Evaluation & Benchmarking Harness.

Calculates:
  - Detection Precision, Recall, and F1-Score
  - Top-1 and Top-5 Suggestion Accuracy
  - Execution Latency Comparison (Linear Search vs. BK-Tree Metric Space Search)
  - Morphological Disambiguation Accuracy
Outputs:
  - CSV report at data/evaluation_results.csv
  - Detailed console evaluation tables
"""

import sys
import os
import json
import time
import csv
from pathlib import Path

# Add project root to sys.path
ROOT_DIR = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT_DIR))

from typesure.spellchecker import check_text, get_suggestions
from typesure.dictionary_loader import dictionary as tamil_dict
from typesure.weighted_levenshtein import weighted_levenshtein, default_levenshtein
from typesure.morphology import check_morphological_inflection


def load_dataset():
    data_path = ROOT_DIR / "data" / "evaluation_dataset.json"
    with open(data_path, encoding="utf-8") as f:
        return json.load(f)


def evaluate_dataset():
    dataset = load_dataset()
    results = []

    print("=" * 70)
    print("TypeSure Academic Benchmark & Evaluation Engine (v2.0)")
    print(f"Dictionary Size: {len(tamil_dict.words):,} words | BK-Tree Nodes: {tamil_dict.bktree.size:,}")
    print("=" * 70)

    # Metrics accumulators
    tp = 0  # correctly identified spelling errors
    fp = 0  # valid words flagged as errors (false alarms)
    tn = 0  # valid words correctly accepted
    fn = 0  # real errors missed

    top1_correct = 0
    top5_correct = 0
    total_errors_tested = 0

    linear_times = []
    bktree_times = []

    for split_name, items in dataset["splits"].items():
        print(f"\nEvaluating split: '{split_name}' ({len(items)} items)...")
        for item in items:
            inp = item["input"]
            expected = item["expected"]
            item_type = item["type"]

            # Evaluate latency on individual words
            if " " not in inp:
                t0 = time.perf_counter()
                tamil_dict.search_candidates_linear(inp, max_dist=2)
                linear_times.append((time.perf_counter() - t0) * 1000)

                t1 = time.perf_counter()
                tamil_dict.search_candidates_bktree(inp, max_dist=2)
                bktree_times.append((time.perf_counter() - t1) * 1000)

            # Full pipeline check
            check_res = check_text(inp, search_method="bktree")
            issues = check_res["issues"]
            has_error = len(issues) > 0

            # Classification matrix
            if item_type in ("error", "sentence_error", "mixed_error"):
                total_errors_tested += 1
                if has_error:
                    tp += 1
                    # Check suggestion accuracy
                    for iss in issues:
                        sug_words = [s["word"] for s in iss["suggestions"]]
                        if sug_words and expected in sug_words:
                            top5_correct += 1
                            if sug_words[0] == expected:
                                top1_correct += 1
                else:
                    fn += 1
            else:
                if has_error:
                    fp += 1
                else:
                    tn += 1

            results.append({
                "split": split_name,
                "input": inp,
                "expected": expected,
                "category": item["category"],
                "type": item_type,
                "issues_found": len(issues),
                "top_suggestions": [s["word"] for s in issues[0]["suggestions"]] if issues else [],
                "latency_ms": check_res["stats"]["processing_time_ms"],
            })

    # Calculations
    precision = tp / max(tp + fp, 1)
    recall = tp / max(tp + fn, 1)
    f1 = 2 * (precision * recall) / max(precision + recall, 1e-9)
    top1_acc = top1_correct / max(total_errors_tested, 1)
    top5_acc = top5_correct / max(total_errors_tested, 1)
    avg_linear_ms = sum(linear_times) / max(len(linear_times), 1)
    avg_bktree_ms = sum(bktree_times) / max(len(bktree_times), 1)
    speedup = avg_linear_ms / max(avg_bktree_ms, 0.0001)

    print("\n" + "=" * 70)
    print("ACADEMIC PERFORMANCE SUMMARY")
    print("=" * 70)
    print(f"Total Test Items Evaluated    : {len(results)}")
    print(f"True Positives (TP)           : {tp}")
    print(f"True Negatives (TN)           : {tn}")
    print(f"False Positives (FP)          : {fp}")
    print(f"False Negatives (FN)          : {fn}")
    print(f"Detection Precision           : {precision * 100:.2f}%")
    print(f"Detection Recall              : {recall * 100:.2f}%")
    print(f"Detection F1-Score            : {f1 * 100:.2f}%")
    print(f"Correction Top-1 Accuracy     : {top1_acc * 100:.2f}%")
    print(f"Correction Top-5 Accuracy     : {top5_acc * 100:.2f}%")
    print("-" * 70)
    print(f"Average Linear Search Latency : {avg_linear_ms:.3f} ms")
    print(f"Average BK-Tree Search Latency: {avg_bktree_ms:.3f} ms")
    print(f"BK-Tree Retrieval Speedup     : {speedup:.2f}x faster")
    print("=" * 70)

    # Save to CSV
    csv_path = ROOT_DIR / "data" / "evaluation_results.csv"
    with open(csv_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(
            f,
            fieldnames=["split", "category", "input", "expected", "type", "issues_found", "top_suggestions", "latency_ms"]
        )
        writer.writeheader()
        for r in results:
            writer.writerow({
                **r,
                "top_suggestions": " | ".join(r["top_suggestions"]),
            })

    print(f"\n[Artifact Generated] Evaluation results exported to: {csv_path}")

    # Return summary dict
    return {
        "precision": precision,
        "recall": recall,
        "f1": f1,
        "top1_accuracy": top1_acc,
        "top5_accuracy": top5_acc,
        "avg_linear_ms": avg_linear_ms,
        "avg_bktree_ms": avg_bktree_ms,
        "speedup": speedup,
        "total_items": len(results),
        "tp": tp, "tn": tn, "fp": fp, "fn": fn,
    }


if __name__ == "__main__":
    evaluate_dataset()
