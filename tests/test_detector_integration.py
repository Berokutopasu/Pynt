import pytest
from tests.fixtures.vulnerable_code_samples import vulnerable_code
from tests.fixtures.expected_findings import expected_findings

def test_detector_integration():
    results = run_detector_integration(vulnerable_code)
    assert results == expected_findings