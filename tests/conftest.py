"""pytest 설정"""

import pytest


def pytest_configure(config):
    """pytest 설정"""
    config.addinivalue_line(
        "markers",
        "integration: marks tests as integration tests (deselect with '-m \"not integration\"')",
    )


@pytest.fixture
def sample_stock_code():
    """테스트용 종목코드"""
    return "005930"  # 삼성전자


@pytest.fixture
def sample_stock_name():
    """테스트용 종목명"""
    return "삼성전자"
