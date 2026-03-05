"""
Test: Verify that Semgrep detects the expected rules for each test file.

Validates that:
- Detected rule IDs match expected_rule_ids from ground_truth
- No unexpected rules are returned (FP = 0)
- All expected rules are found for reviewed cases
"""

import pytest
import json
import sys
import os
from pathlib import Path
from typing import Dict, List, Set

# Import pynt server components
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "server"))
from analyzers.semgrep_analyzer import SemgrepAnalyzer
from models.schemas import AnalysisType

# --- SETUP ---
TEST_DIR = Path(__file__).resolve().parent  # tests/ directory
SECURITY_TEST_DIR = TEST_DIR / "Security_test"
GROUND_TRUTH_FILE = SECURITY_TEST_DIR / "ground_truth.json"


def load_ground_truth() -> Dict:
    """Load ground truth manifest."""
    if not GROUND_TRUTH_FILE.exists():
        raise FileNotFoundError(f"Ground truth not found at {GROUND_TRUTH_FILE}")
    return json.loads(GROUND_TRUTH_FILE.read_text(encoding="utf-8"))


def _prepare_semgrep_env() -> None:
    """Ensure SemgrepAnalyzer can discover semgrep in non-activated venv runs."""
    venv_root = str(Path(sys.executable).resolve().parents[1])
    scripts_dir = str(Path(venv_root) / "Scripts")
    os.environ.setdefault("VIRTUAL_ENV", venv_root)
    if scripts_dir not in os.environ.get("PATH", ""):
        os.environ["PATH"] = f"{scripts_dir}{os.pathsep}" + os.environ.get("PATH", "")


def _normalize_rule_id(check_id: str) -> str | None:
    """Map semgrep check IDs to canonical `pynt-*` IDs and ignore non-pynt rules."""
    if not check_id:
        return None
    if "pynt-" not in check_id:
        return None
    normalized = check_id.split(".")[-1]
    if normalized == "pynt-debug-execute-check":
        return None
    return normalized


def analyze_security(code: str, filename: str = None) -> Set[str]:
    """
    Execute Semgrep on code and return detected rule IDs.
    
    Args:
        code: Python source code to analyze
        filename: Original filename (for context, optional)
    
    Returns:
        Set of detected rule IDs (check_id from SemgrepResult)
    """
    _prepare_semgrep_env()
    analyzer = SemgrepAnalyzer()
    semgrep_results = analyzer.analyze(
        code=code,
        language="python",
        analysis_type=AnalysisType.SECURITY,
        filename=filename,
        project_path=None,
        extra_targets=None
    )
    
    # Keep only local pynt rules and normalize prefixed ids.
    detected_rule_ids = {
        normalized
        for result in semgrep_results
        for normalized in [_normalize_rule_id(result.check_id)]
        if normalized
    }
    return detected_rule_ids


# --- PARAMETRIZED TESTS ---
@pytest.mark.parametrize("case", load_ground_truth()["cases"])
def test_security_analysis_per_file(case):
    """
    Test that analyzed file returns exactly the expected rule IDs.
    
    For reviewed cases: strict validation (must match exactly)
    For draft cases: informational only (skip assertion since gaps are known)
    """
    filename = case["file"]
    expected_rule_ids = set(case["expected_rule_ids"])
    review_status = case["review_status"]
    target_file = SECURITY_TEST_DIR / filename
    
    # Read and analyze file
    code = target_file.read_text(encoding="utf-8")
    detected_rule_ids = analyze_security(code, str(target_file))
    
    # Compute metrics
    tp = expected_rule_ids & detected_rule_ids  # True Positives
    fp = detected_rule_ids - expected_rule_ids  # False Positives
    fn = expected_rule_ids - detected_rule_ids  # False Negatives
    
    # Log results
    print(f"\n{filename} ({review_status}):")
    print(f"  Expected: {sorted(expected_rule_ids) if expected_rule_ids else '(none)'}")
    print(f"  Detected: {sorted(detected_rule_ids) if detected_rule_ids else '(none)'}")
    if tp:
        print(f"  ✓ TP: {sorted(tp)}")
    if fp:
        print(f"  ✗ FP: {sorted(fp)}")
    if fn:
        print(f"  ✗ FN: {sorted(fn)}")
    
    # Validate based on review status
    if review_status == "reviewed":
        # Strict: must match exactly
        assert detected_rule_ids == expected_rule_ids, (
            f"{filename}: Expected {expected_rule_ids}, got {detected_rule_ids}. "
            f"TP={tp}, FP={fp}, FN={fn}"
        )
    elif review_status == "draft":
        # Informational: document mismatches as known catalog gaps
        if detected_rule_ids != expected_rule_ids:
            print(f"  ⚠️  DRAFT case - known catalog gap: FP={fp}, FN={fn}")


@pytest.mark.parametrize("case", [c for c in load_ground_truth()["cases"] if c["review_status"] == "reviewed"])
def test_security_analysis_reviewed_only(case):
    """
    Strict validation: Only tested on 'reviewed' cases with high confidence.
    
    For each reviewed file:
    - No false positives allowed (FP = 0)
    - No false negatives allowed (FN = 0)  
    - Detected rules must match expected_rule_ids exactly
    """
    filename = case["file"]
    expected_rule_ids = set(case["expected_rule_ids"])
    target_file = SECURITY_TEST_DIR / filename
    
    code = target_file.read_text(encoding="utf-8")
    detected_rule_ids = analyze_security(code, str(target_file))
    
    fp = detected_rule_ids - expected_rule_ids
    fn = expected_rule_ids - detected_rule_ids
    
    # Strict: no false positives for reviewed cases
    assert len(fp) == 0, (
        f"{filename}: Unexpected false positives: {sorted(fp)}. "
        f"Expected: {expected_rule_ids}"
    )
    
    # Strict: no false negatives for reviewed cases
    assert len(fn) == 0, (
        f"{filename}: Missed detections (false negatives): {sorted(fn)}. "
        f"Expected: {expected_rule_ids}, Got: {detected_rule_ids}"
    )


def test_security_analysis_aggregate_metrics():
    """
    Compute and report aggregate metrics across all reviewed cases.
    
    Validates:
    - Precision: TP / (TP + FP)
    - Recall: TP / (TP + FN)
    - F1 Score: 2 * (P * R) / (P + R)
    """
    gt = load_ground_truth()
    reviewed_cases = [c for c in gt["cases"] if c["review_status"] == "reviewed"]
    
    total_tp = 0
    total_fp = 0
    total_fn = 0
    
    for case in reviewed_cases:
        filename = case["file"]
        expected_rule_ids = set(case["expected_rule_ids"])
        target_file = SECURITY_TEST_DIR / filename
        
        code = target_file.read_text(encoding="utf-8")
        detected_rule_ids = analyze_security(code, str(target_file))
        
        tp = len(expected_rule_ids & detected_rule_ids)
        fp = len(detected_rule_ids - expected_rule_ids)
        fn = len(expected_rule_ids - detected_rule_ids)
        
        total_tp += tp
        total_fp += fp
        total_fn += fn
    
    # Calculate metrics
    precision = total_tp / (total_tp + total_fp) if (total_tp + total_fp) > 0 else 0.0
    recall = total_tp / (total_tp + total_fn) if (total_tp + total_fn) > 0 else 0.0
    f1 = 2 * (precision * recall) / (precision + recall) if (precision + recall) > 0 else 0.0
    
    # Report
    print("\n" + "="*70)
    print("AGGREGATE METRICS (Reviewed Cases Only)")
    print("="*70)
    print(f"True Positives:  {total_tp}")
    print(f"False Positives: {total_fp}")
    print(f"False Negatives: {total_fn}")
    print(f"\nPrecision: {precision:.3f} (target: ≥ 0.80)")
    print(f"Recall:    {recall:.3f} (target: ≥ 0.85)")
    print(f"F1 Score:  {f1:.3f} (target: ≥ 0.82)")
    print("="*70)
    
    # Validate against targets
    assert precision >= 0.80, f"Precision {precision:.3f} below target 0.80"
    assert recall >= 0.85, f"Recall {recall:.3f} below target 0.85"
    assert f1 >= 0.82, f"F1 Score {f1:.3f} below target 0.82"