import pytest

from formflow.fixtures import FIXTURE_DESCRIPTIONS, generate_fixtures


@pytest.fixture
def fixture_dir(tmp_path):
    path = tmp_path / "fixtures"
    generate_fixtures(path)
    return path


@pytest.fixture
def descriptions():
    return FIXTURE_DESCRIPTIONS
