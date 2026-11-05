import pytest

from sap_sd_agent.gemini_api import check_gemini


@pytest.mark.integration
def test_live_gemini_api():
    answer = check_gemini()
    assert answer
