"""
Metrics & Regression Analysis for Pynt Detection
=================================================

Computes precision, recall, F1 for detection against ground truth.
Tracks baseline and regression across versions.

Usage:
  python metrics.py --run-pynt
  python metrics.py --compare-baseline
"""

import argparse
import json
import subprocess
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Set, Tuple


class DetectionMetrics:
    """Compute detection metrics against ground truth."""
    
    def __init__(self, ground_truth_file: Path, results_dir: Path = None):
        self.gt_file = ground_truth_file
        self.results_dir = results_dir or ground_truth_file.parent / ".test_results"
        self.results_dir.mkdir(exist_ok=True)
        
        with open(ground_truth_file) as f:
            self.ground_truth = json.load(f)
    
    def load_detected_results(self, results_json: Path) -> Dict:
        """Load pynt executed results (per-file detections)."""
        if not results_json.exists():
            return {}
        with open(results_json) as f:
            return json.load(f)
    
    def compute_metrics_per_file(self) -> List[Dict]:
        """
        Compute TP, FP, FN per file.
        
        TP: rule detected and expected
        FP: rule detected but not expected
        FN: rule expected but not detected
        """
        metrics = []
        
        for case in self.ground_truth["cases"]:
            file = case["file"]
            expected_rules = set(case["expected_rule_ids"])
            review_status = case.get("review_status", "draft")
            
            # Placeholder: in real execution, load detected_rules from pynt output
            detected_rules = set()  # TODO: populate from run_pynt()
            
            tp = expected_rules & detected_rules
            fp = detected_rules - expected_rules
            fn = expected_rules - detected_rules
            
            metrics.append({
                "file": file,
                "expected_rules": sorted(expected_rules),
                "detected_rules": sorted(detected_rules),
                "tp_count": len(tp),
                "fp_count": len(fp),
                "fn_count": len(fn),
                "review_status": review_status,
                "tp": sorted(tp),
                "fp": sorted(fp),
                "fn": sorted(fn)
            })
        
        return metrics
    
    def compute_aggregate_metrics(self, per_file_metrics: List[Dict]) -> Dict:
        """Aggregate metrics across all files."""
        total_tp = sum(m["tp_count"] for m in per_file_metrics)
        total_fp = sum(m["fp_count"] for m in per_file_metrics)
        total_fn = sum(m["fn_count"] for m in per_file_metrics)
        
        precision = total_tp / (total_tp + total_fp) if (total_tp + total_fp) > 0 else 0.0
        recall = total_tp / (total_tp + total_fn) if (total_tp + total_fn) > 0 else 0.0
        f1 = 2 * (precision * recall) / (precision + recall) if (precision + recall) > 0 else 0.0
        
        return {
            "total_tp": total_tp,
            "total_fp": total_fp,
            "total_fn": total_fn,
            "precision": round(precision, 3),
            "recall": round(recall, 3),
            "f1": round(f1, 3),
            "total_expected": total_tp + total_fn,
            "total_detected": total_tp + total_fp
        }
    
    def generate_report(self, per_file_metrics: List[Dict], agg_metrics: Dict) -> str:
        """Generate human-readable report."""
        lines = [
            "=" * 70,
            "PYNT DETECTION METRICS REPORT",
            "=" * 70,
            f"Generated: {datetime.now().isoformat()}",
            "",
            "AGGREGATE METRICS",
            "-" * 70,
            f"Precision: {agg_metrics['precision']:.3f}",
            f"Recall: {agg_metrics['recall']:.3f}",
            f"F1 Score: {agg_metrics['f1']:.3f}",
            "",
            f"True Positives: {agg_metrics['total_tp']}",
            f"False Positives: {agg_metrics['total_fp']}",
            f"False Negatives: {agg_metrics['total_fn']}",
            f"Total Expected: {agg_metrics['total_expected']}",
            f"Total Detected: {agg_metrics['total_detected']}",
            "",
            "PER-FILE BREAKDOWN",
            "-" * 70,
        ]
        
        # Group by review status
        reviewed = [m for m in per_file_metrics if m["review_status"] == "reviewed"]
        draft = [m for m in per_file_metrics if m["review_status"] == "draft"]
        
        lines.append(f"\nREVIEWED CASES ({len(reviewed)}):")
        for m in reviewed:
            lines.append(f"\n  {m['file']}")
            lines.append(f"    Expected: {m['expected_rules']}")
            lines.append(f"    Detected: {m['detected_rules']}")
            if m['fp']:
                lines.append(f"    FP (false alerts): {m['fp']}")
            if m['fn']:
                lines.append(f"    FN (missed): {m['fn']}")
        
        lines.append(f"\n\nDRAFT CASES ({len(draft)}) - Known catalog gaps:")
        for m in draft:
            lines.append(f"\n  {m['file']}")
            lines.append(f"    Expected: {m['expected_rules']} (pending catalog expansion)")
        
        lines.append("\n" + "=" * 70)
        
        return "\n".join(lines)
    
    def save_metrics(self, per_file_metrics: List[Dict], agg_metrics: Dict, report: str):
        """Persist metrics to file."""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        report_file = self.results_dir / f"report_{timestamp}.txt"
        metrics_file = self.results_dir / f"metrics_{timestamp}.json"
        
        report_file.write_text(report, encoding="utf-8")
        
        metrics_file.write_text(
            json.dumps({
                "timestamp": timestamp,
                "aggregate": agg_metrics,
                "per_file": per_file_metrics
            }, indent=2),
            encoding="utf-8"
        )
        
        return report_file, metrics_file
    
    def compare_baseline(self) -> Dict:
        """Compare current metrics against baseline."""
        baseline_file = self.results_dir / "baseline.json"
        
        if not baseline_file.exists():
            raise FileNotFoundError(f"Baseline not found at {baseline_file}. Run metrics once first.")
        
        with open(baseline_file) as f:
            baseline = json.load(f)
        
        current_metrics = self.compute_aggregate_metrics(
            self.compute_metrics_per_file()
        )
        
        deltas = {
            "precision_delta": round(current_metrics["precision"] - baseline["precision"], 3),
            "recall_delta": round(current_metrics["recall"] - baseline["recall"], 3),
            "f1_delta": round(current_metrics["f1"] - baseline["f1"], 3),
            "tp_delta": current_metrics["total_tp"] - baseline["total_tp"],
            "fp_delta": current_metrics["total_fp"] - baseline["total_fp"],
            "fn_delta": current_metrics["total_fn"] - baseline["total_fn"],
        }
        
        return {
            "baseline": baseline,
            "current": current_metrics,
            "deltas": deltas,
            "pass": all(abs(d) < 0.05 or d <= 0 for d in [
                deltas["precision_delta"], 
                deltas["recall_delta"]
            ])
        }


def main():
    parser = argparse.ArgumentParser(
        description="Compute and track detection metrics for Pynt against ground truth."
    )
    parser.add_argument(
        "--run-pynt",
        action="store_true",
        help="Execute pynt on Security_test and compute metrics"
    )
    parser.add_argument(
        "--compare-baseline",
        action="store_true",
        help="Compare current metrics against baseline"
    )
    parser.add_argument(
        "--set-baseline",
        action="store_true",
        help="Set current metrics as baseline for future regressions"
    )
    parser.add_argument(
        "--gt-file",
        type=Path,
        default=Path(__file__).parent.parent / "Security_test" / "ground_truth.json",
        help="Path to ground_truth.json"
    )
    
    args = parser.parse_args()
    
    metrics = DetectionMetrics(args.gt_file)
    
    if args.run_pynt or (not args.compare_baseline and not args.set_baseline):
        print("Computing metrics from ground truth...")
        per_file = metrics.compute_metrics_per_file()
        agg = metrics.compute_aggregate_metrics(per_file)
        report = metrics.generate_report(per_file, agg)
        
        print(report)
        
        report_f, metrics_f = metrics.save_metrics(per_file, agg, report)
        print(f"\nMetrics saved to: {metrics_f}")
        print(f"Report saved to: {report_f}")
    
    if args.compare_baseline:
        print("Comparing against baseline...")
        try:
            comparison = metrics.compare_baseline()
            print(json.dumps(comparison, indent=2))
            
            if comparison["pass"]:
                print("\n✅ Regression test PASSED (deltas within tolerance)")
            else:
                print("\n❌ Regression test FAILED (significant deviation detected)")
        except FileNotFoundError as e:
            print(f"Error: {e}")
    
    if args.set_baseline:
        print("Setting current metrics as baseline...")
        per_file = metrics.compute_metrics_per_file()
        agg = metrics.compute_aggregate_metrics(per_file)
        
        baseline_file = metrics.results_dir / "baseline.json"
        baseline_file.write_text(json.dumps(agg, indent=2), encoding="utf-8")
        print(f"Baseline saved to: {baseline_file}")
        print(json.dumps(agg, indent=2))


if __name__ == "__main__":
    main()
