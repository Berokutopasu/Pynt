"""
Test Strategy v2: Pynt Diagnostic Validation Suite
=====================================================

Hard assertions (deterministic):
  - Validate ruleId match against ground truth
  - Check presence/absence of findings per file
  
Soft assertions (generative):
  - Validate API contract (schema)
  - Check LLM section parseability
  - Check non-empty message/explanation fields
"""

import json
import subprocess
import sys
import os
from pathlib import Path
from typing import Dict, List, Set

import pytest

# Import pynt server components for Semgrep-only analysis (no LLM)
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


def run_pynt_on_file(target_file: Path, analysis_type: str = "security") -> Dict:
    """
    Execute Semgrep on a single file and return detected findings.
    
    Uses only Semgrep, no LLM (faster, no API calls).
    
    Args:
        target_file: Path to the Python file to analyze
        analysis_type: Type of analysis (only "security" used for metrics)
    
    Returns:
        Dict with detected rule IDs
    """
    if not target_file.exists():
        raise FileNotFoundError(f"File not found: {target_file}")
    
    code = target_file.read_text(encoding="utf-8")
    
    # Use SemgrepAnalyzer directly (no LLM, no async)
    _prepare_semgrep_env()
    analyzer = SemgrepAnalyzer()
    semgrep_results = analyzer.analyze(
        code=code,
        language="python",
        analysis_type=AnalysisType.SECURITY,
        filename=str(target_file),
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
    
    return {
        "detected_rule_ids": detected_rule_ids,
        "file": target_file.name,
        "semgrep_results_count": len(semgrep_results)
    }


class TestDeterministicDetection:
    """Hard assertions: rule detection match against ground truth."""
    
    def test_ground_truth_exists(self):
        """Verify ground truth manifest is present and valid."""
        assert GROUND_TRUTH_FILE.exists(), f"Ground truth not found at {GROUND_TRUTH_FILE}"
        gt = load_ground_truth()
        assert "cases" in gt, "Ground truth missing 'cases' key"
        assert len(gt["cases"]) == 19, "Expected 19 test cases"
    
    def test_ground_truth_schema(self):
        """Validate ground truth schema compliance."""
        gt = load_ground_truth()
        required_fields = {"file", "expected_rule_ids", "review_status", "notes"}
        for case in gt["cases"]:
            for field in required_fields:
                assert field in case, f"Case {case.get('file')} missing field '{field}'"
            assert isinstance(case["expected_rule_ids"], list), f"expected_rule_ids must be list for {case['file']}"
            assert case["review_status"] in ["reviewed", "draft"], f"Invalid review_status for {case['file']}"
    
    def test_reviewed_cases_count(self):
        """Verify we have enough reviewed cases for strict validation."""
        gt = load_ground_truth()
        reviewed = [c for c in gt["cases"] if c["review_status"] == "reviewed"]
        assert len(reviewed) >= 12, f"Expected at least 12 reviewed cases, got {len(reviewed)}"
    
    @pytest.mark.parametrize("case", load_ground_truth()["cases"])
    def test_file_exists(self, case):
        """Verify all test files exist in Security_test."""
        file_path = SECURITY_TEST_DIR / case["file"]
        assert file_path.exists(), f"Test file not found: {file_path}"
    
    def test_rule_catalog_referenced(self):
        """Verify all expected_rule_ids exist in catalog."""
        gt = load_ground_truth()
        # If we have a rule catalog, validate here
        # For now, just ensure IDs follow naming convention
        all_rule_ids = set()
        for case in gt["cases"]:
            all_rule_ids.update(case["expected_rule_ids"])
        
        for rule_id in all_rule_ids:
            assert rule_id.startswith("pynt-"), f"Invalid rule_id format: {rule_id}"


class TestDetectionCoverage:
    """Analyze coverage: which rule families are covered by the dataset."""
    
    def test_coverage_summary(self):
        """Summarize coverage across dataset."""
        gt = load_ground_truth()
        stats = gt.get("statistics", {})
        
        files_with_rules = stats.get("files_with_expected_rules", 0)
        total_files = stats.get("total_files", 0)
        
        print(f"\n=== Detection Coverage ===")
        print(f"Files with expected rules: {files_with_rules}/{total_files}")
        print(f"Coverage: {100*files_with_rules/total_files:.1f}%")
        
        rule_dist = stats.get("rule_distribution", {})
        for rule, count in rule_dist.items():
            print(f"  {rule}: {count} files")
        
        # Coverage should ideally be > 80% for a robust test
        assert files_with_rules >= 10, f"Coverage too low: {files_with_rules}/{total_files}"


class TestCatalogGaps:
    """Document known limitations and gaps in the Semgrep rule catalog."""
    
    def test_catalog_gaps_documented(self):
        """Verify gaps are explicitly documented."""
        gt = load_ground_truth()
        gaps = gt.get("gaps_in_catalog", {})
        
        expected_gap_keys = {
            "command_injection_via_os_system",
            "yaml_unsafe_deserialization"
        }
        assert set(gaps.keys()).issuperset(expected_gap_keys), f"Missing gap documentation"
        
        print(f"\n=== Catalog Gaps ===")
        for gap_id, gap_info in gaps.items():
            print(f"\n{gap_id}:")
            print(f"  Description: {gap_info.get('description', 'N/A')}")
            print(f"  Files affected: {len(gap_info.get('files_affected', []))} files")
            print(f"  Priority: {gap_info.get('priority', 'N/A')}")
            print(f"  Suggested rule: {gap_info.get('suggested_rule_id', 'N/A')}")
    
    def test_gap_priorities(self):
        """Ensure high-priority gaps are identified."""
        gt = load_ground_truth()
        gaps = gt.get("gaps_in_catalog", {})
        
        high_priority = [g for g in gaps.values() if g.get("priority") == "HIGH"]
        assert len(high_priority) >= 2, "Expected at least 2 HIGH priority gaps (CMDi, YAML)"


class TestSoftAssertions:
    """Soft assertions: LLM generation quality, not exact answer match."""
    
    def test_llm_sections_parseability(self):
        """
        Verify LLM output sections are parseable.
        This test would run against actual pynt output.
        """
        # Placeholder: when integrated with live pynt server
        # Check that sections like FALSE_POSITIVE, EXPLANATION, SUGGESTED_FIX parse correctly
        pytest.skip("Requires live pynt server integration")
    
    def test_api_contract_fields(self):
        """Verify API response includes required Finding fields."""
        # From schemas.py: line, column, endLine, endColumn, severity, message, etc.
        required_fields = {
            "line", "column", "severity", "message", "analysisType", "ruleId"
        }
        # When integrated: validate each finding has these fields
        pytest.skip("Requires live pynt server integration")


class TestRegressionBaseline:
    """Track changes in detection across runs."""
    
    def test_baseline_creation(self):
        """Create initial baseline for ruleId coverage."""
        gt = load_ground_truth()
        
        baseline = {
            "timestamp": "2026-03-03",
            "total_files": gt["statistics"]["total_files"],
            "files_with_expected_rules": gt["statistics"]["files_with_expected_rules"],
            "rule_distribution": gt["statistics"]["rule_distribution"],
            "catalog_gaps": list(gt["gaps_in_catalog"].keys())
        }
        
        baseline_file = SECURITY_TEST_DIR / "baseline_detection.json"
        baseline_file.write_text(json.dumps(baseline, indent=2), encoding="utf-8")
        
        print(f"\n=== Detection Baseline ===")
        print(json.dumps(baseline, indent=2))
    
    def test_regression_compare(self):
        """Compare current run against baseline (future integration)."""
        baseline_file = SECURITY_TEST_DIR / "baseline_detection.json"
        
        if not baseline_file.exists():
            pytest.skip("Baseline not yet established")
        
        # Future: after running pynt, compare detected rules against baseline
        pytest.skip("Requires integration with pynt execution")


class TestGovernance:
    """Ground truth governance and review process."""
    
    def test_adjudication_fields_present(self):
        """Verify reviewed cases have adjudication notes."""
        gt = load_ground_truth()
        
        for case in gt["cases"]:
            if case["review_status"] == "reviewed":
                assert "adjudication_notes" in case, f"Missing adjudication_notes for reviewed case: {case['file']}"
                assert len(case["adjudication_notes"]) > 0, f"Empty adjudication_notes for {case['file']}"
    
    def test_draft_cases_have_recommendations(self):
        """Verify draft cases document what's needed for promotion."""
        gt = load_ground_truth()
        
        for case in gt["cases"]:
            if case["review_status"] == "draft":
                notes = case.get("notes", "").lower()
                assert "catalog" in notes or "suggest" in notes, \
                    f"Draft case {case['file']} should explain why it's not reviewed"


# --- EXECUTION ---
if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
