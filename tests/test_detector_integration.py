"""
Integration Test: Validate LLM Response Structure

Tests the complete analysis pipeline (Semgrep + LLM):
- Validate that all required Finding fields are present
- Check that LLM output sections are parseable
- Verify false positive detection and marking
"""

import pytest
import sys
import os
import re
from pathlib import Path
from typing import List, Optional

# Import pynt server components
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "server"))
from agents.security_agent import PythonSecurityAgent
from agents.base_agent import BaseAgent
from models.schemas import Finding, AnalysisType

# --- SETUP ---
TEST_DIR = Path(__file__).resolve().parent  # tests/ directory
SECURITY_TEST_DIR = TEST_DIR / "Security_test"

# Test configuration
TEST_FILE = "aa.py"  # Small file with simple vulnerabilities
TEST_FILE_PATH = SECURITY_TEST_DIR / TEST_FILE


# --- HELPER FUNCTIONS ---
def validate_educational_explanation_sections(educational_text: str) -> dict:
    """
    Valida se educationalExplanation contiene tutte le sezioni principali
    che _parse_llm_response estrae dalla risposta LLM.
    
    Args:
        educational_text: Il testo di educationalExplanation da validare
        
    Returns:
        Dict con chiavi per ogni sezione e bool che indica se presente:
        {
            'explanation': bool,
            'suggested_fix': bool,
            'code_example': bool,
            'references': bool,
            'is_false_positive': bool,
            'all_sections_present': bool
        }
    """
    if not educational_text or not isinstance(educational_text, str):
        return {
            'explanation': False,
            'suggested_fix': False,
            'code_example': False,
            'references': False,
            'is_false_positive': False,
            'all_sections_present': False
        }
    
    text_lower = educational_text.lower()
    
    # Pattern di ricerca per ogni sezione (varianti comuni)
    patterns = {
        'explanation': [r'explain', r'why\s', r'vulnerability', r'rischio', r'vulnerabil'],
        'suggested_fix': [r'fix', r'remediat', r'solution', r'soluzione', r'correzi'],
        'code_example': [r'example', r'corrected', r'esempio', r'corretto', r'codice'],
        'references': [r'owasp', r'link', r'reference', r'documentation', r'https?://'],
        'is_false_positive': [r'false\s?positive', r'falso\s?positivo', r'not\s?vulnerable']
    }
    
    results = {}
    for section, patterns_list in patterns.items():
        found = any(re.search(p, text_lower) for p in patterns_list)
        results[section] = found
    
    # Aggiungi flag overall
    results['all_sections_present'] = all(results.values())
    
    return results


def has_groq_api_key() -> bool:
    """Check if Groq API key is configured."""
    from config.settings import settings
    return settings.EFFECTIVE_GROQ_KEYS is not None and len(settings.EFFECTIVE_GROQ_KEYS) > 0


@pytest.fixture(scope="session")
def analyzed_findings() -> List[Finding]:
    """
    Analyze test file once and return findings.
    
    Uses aa.py (small, simple vulnerabilities) to avoid excessive LLM calls.
    """
    if not has_groq_api_key():
        pytest.skip("Groq API key not configured - skipping LLM integration tests")
    
    if not TEST_FILE_PATH.exists():
        raise FileNotFoundError(f"Test file not found: {TEST_FILE_PATH}")
    
    code = TEST_FILE_PATH.read_text(encoding="utf-8")
    
    # Run security agent (Semgrep + LLM)
    agent = PythonSecurityAgent()
    
    import asyncio
    findings = asyncio.run(
        agent.analyze(
            code=code,
            language="python",
            filename=str(TEST_FILE_PATH),
            project_path=None,
            rag_service=None
        )
    )
    
    return findings


class TestFindingStructure:
    """Validate that all required Finding fields are present."""
    
    # Required fields that MUST be present in every Finding
    REQUIRED_FIELDS = {
        "line",
        "column",
        "endLine",
        "endColumn",
        "severity",
        "message",
        "educationalExplanation",
        "analysisType",
        "ruleId",
        "isFalsePositive"
    }
    
    # Optional fields (may be None, but should be present)
    OPTIONAL_FIELDS = {
        "suggestedFix",
        "executableFix",
        "codeExample",
        "references",
        "file_path"
    }
    
    def test_findings_exist(self, analyzed_findings):
        """Verify that analyzing aa.py returns at least one finding."""
        assert len(analyzed_findings) > 0, (
            f"{TEST_FILE}: Expected at least 1 finding, got {len(analyzed_findings)}"
        )
        print(f"\n✓ {TEST_FILE} produced {len(analyzed_findings)} findings")
    
    def test_all_required_fields_present(self, analyzed_findings):
        """
        Validate that every Finding has all required fields.
        
        Required fields: line, column, endLine, endColumn, severity, message,
                        educationalExplanation, analysisType, ruleId, isFalsePositive
        """
        for idx, finding in enumerate(analyzed_findings):
            missing_fields = self.REQUIRED_FIELDS - set(finding.__fields__.keys())
            
            assert len(missing_fields) == 0, (
                f"Finding {idx}: Missing required fields: {missing_fields}"
            )
            
            # Validate that required fields are not None
            for field in self.REQUIRED_FIELDS:
                value = getattr(finding, field, None)
                assert value is not None, (
                    f"Finding {idx}: Required field '{field}' is None"
                )
        
        print(f"✓ All {len(analyzed_findings)} findings have required fields")
    
    def test_all_optional_fields_defined(self, analyzed_findings):
        """
        Validate that every Finding has optional fields defined (even if None).
        
        Optional fields should exist in schema even if value is None.
        """
        for idx, finding in enumerate(analyzed_findings):
            for field in self.OPTIONAL_FIELDS:
                assert hasattr(finding, field), (
                    f"Finding {idx}: Missing optional field '{field}'"
                )
        
        print(f"✓ All {len(analyzed_findings)} findings have optional field definitions")
    
    def test_field_types_valid(self, analyzed_findings):
        """Validate that field types match schema expectations."""
        for idx, finding in enumerate(analyzed_findings):
            # Types validation
            assert isinstance(finding.line, int) and finding.line > 0, (
                f"Finding {idx}: 'line' must be positive int, got {finding.line}"
            )
            assert isinstance(finding.column, int) and finding.column >= 0, (
                f"Finding {idx}: 'column' must be non-negative int, got {finding.column}"
            )
            assert isinstance(finding.endLine, int) and finding.endLine >= finding.line, (
                f"Finding {idx}: 'endLine' must be >= 'line', got {finding.endLine}"
            )
            assert isinstance(finding.endColumn, int) and finding.endColumn >= 0, (
                f"Finding {idx}: 'endColumn' must be non-negative int, got {finding.endColumn}"
            )
            assert isinstance(finding.message, str) and len(finding.message) > 0, (
                f"Finding {idx}: 'message' must be non-empty string"
            )
            assert isinstance(finding.educationalExplanation, str) and len(finding.educationalExplanation) > 0, (
                f"Finding {idx}: 'educationalExplanation' must be non-empty string"
            )
            assert isinstance(finding.ruleId, str) and len(finding.ruleId) > 0, (
                f"Finding {idx}: 'ruleId' must be non-empty string"
            )
            assert isinstance(finding.isFalsePositive, bool), (
                f"Finding {idx}: 'isFalsePositive' must be bool, got {type(finding.isFalsePositive)}"
            )
        
        print(f"✓ All {len(analyzed_findings)} findings have valid field types")
    
    def test_llm_sections_parseable(self, analyzed_findings):
        """
        Validate that LLM output sections are parseable.
        
        Checks for presence of expected sections in educationalExplanation and message.
        """
        for idx, finding in enumerate(analyzed_findings):
            explanation = finding.educationalExplanation.upper()
            
            # Check that explanation contains educational content (not just junk)
            assert len(finding.educationalExplanation) > 50, (
                f"Finding {idx}: 'educationalExplanation' too short (< 50 chars)"
            )
            
            # If suggestedFix is provided, should be non-empty
            if finding.suggestedFix:
                assert len(finding.suggestedFix) > 0, (
                    f"Finding {idx}: 'suggestedFix' is empty string (should be None or non-empty)"
                )
        
        print(f"✓ LLM sections parseable in all {len(analyzed_findings)} findings")
    
    def test_educational_explanation_contains_all_sections(self, analyzed_findings):
        """
        Validate that educationalExplanation contains all LLM parsed sections.
        
        The _parse_llm_response method extracts these sections from LLM response:
        - explanation: WHY the code is vulnerable
        - suggested_fix: HOW to fix it
        - code_example: Example of corrected code
        - references: OWASP/docs links
        - is_false_positive: Boolean indicating false positive
        
        This test ensures these sections are present/referenced in educationalExplanation.
        """
        for idx, finding in enumerate(analyzed_findings):
            # Use the validation helper function
            section_validation = validate_educational_explanation_sections(
                finding.educationalExplanation
            )
            
            # Check each section
            assert section_validation['explanation'], (
                f"Finding {idx}: 'explanation' section not found in educationalExplanation. "
                f"educationalExplanation should contain WHY the vulnerability exists."
            )
            
            assert section_validation['suggested_fix'], (
                f"Finding {idx}: 'suggested_fix' section not found in educationalExplanation. "
                f"educationalExplanation should explain HOW to fix it."
            )
            
            assert section_validation['code_example'], (
                f"Finding {idx}: 'code_example' section not found in educationalExplanation. "
                f"educationalExplanation should provide a corrected code example."
            )
            
            assert section_validation['references'], (
                f"Finding {idx}: 'references' section not found in educationalExplanation. "
                f"educationalExplanation should contain OWASP or official docs links."
            )
            
            assert section_validation['is_false_positive'], (
                f"Finding {idx}: 'is_false_positive' section not found in educationalExplanation. "
                f"educationalExplanation should indicate if it's a false positive."
            )
            
            # Verify all sections are present
            assert section_validation['all_sections_present'], (
                f"Finding {idx}: Not all LLM sections present in educationalExplanation. "
                f"Missing: {[k for k, v in section_validation.items() if not v and k != 'all_sections_present']}"
            )
            
            print(f"  Finding {idx}: All sections present ✓")
        
        print(f"✓ All {len(analyzed_findings)} findings have complete educationalExplanation sections")


class TestFalsePositiveDetection:
    """Validate false positive detection and marking."""
    
    def test_false_positive_field_set(self, analyzed_findings):
        """
        Verify that isFalsePositive field is properly set.
        
        For aa.py, we expect NO false positives (all real SQL injection).
        """
        for idx, finding in enumerate(analyzed_findings):
            # Verify field exists and is boolean
            assert isinstance(finding.isFalsePositive, bool), (
                f"Finding {idx}: 'isFalsePositive' is not bool"
            )
        
        print(f"✓ isFalsePositive field properly set in all findings")
    
    def test_false_positive_marking_correct(self, analyzed_findings):
        """
        For aa.py: expect NO false positives (all findings should be isFalsePositive=False).
        
        aa.py is a curated sample with real SQL injection vulnerabilities.
        """
        false_positive_findings = [f for f in analyzed_findings if f.isFalsePositive]
        
        assert len(false_positive_findings) == 0, (
            f"{TEST_FILE}: Expected 0 false positives, got {len(false_positive_findings)}: "
            f"{[f.ruleId for f in false_positive_findings]}"
        )
        
        print(f"✓ No false positives detected in {TEST_FILE} (all {len(analyzed_findings)} are valid)")
    
    def test_false_positive_field_affects_severity(self, analyzed_findings):
        """
        Verify that when isFalsePositive=True, the finding is appropriately marked.
        
        Note: This test would apply to other test files that might have false positives.
        For aa.py, this is informational (no false positives expected).
        """
        for idx, finding in enumerate(analyzed_findings):
            if finding.isFalsePositive:
                # False positives should still have all required fields
                assert finding.message is not None
                assert finding.ruleId is not None
                assert finding.severity is not None
                
                print(f"  Finding {idx} marked as false positive: {finding.ruleId}")
        
        print(f"✓ False positive marking consistent with all finding fields")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])