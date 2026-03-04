import pytest

@pytest.fixture(scope='session')
def setup_database():
    # Code to set up the database
    yield
    # Code to tear down the database

@pytest.fixture
def sample_vulnerable_code():
    return "print('This is a vulnerable code sample')"

@pytest.fixture
def expected_findings():
    return {
        "findings": [
            {
                "type": "vulnerability",
                "description": "Example vulnerability description"
            }
        ]
    }