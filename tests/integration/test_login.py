import os
import time

import pytest

from tradingTOT.utils.browser_utils import login_tradingTOT, get_login_token
from tests.conftest import clear_browser


TRADINGTOT_URLS = ["https://live.trading212.com/", "https://demo.trading212.com/"]


@pytest.mark.order("first")
def test_login_correct_details(driver, test_env):
    username = os.environ["TRADINGTOT_EMAIL"]
    password = os.environ["TRADINGTOT_PASSWORD"]

    clear_browser(driver)

    assert get_login_token(driver=driver) is None
    driver = login_tradingTOT(driver, username, password)

    # Waiting till the browser's page changes as the change does not happen immediately and this may lead to the
    # failure of the token extraction.
    max_wait = 3
    while max_wait or (driver.current_url not in TRADINGTOT_URLS):
        time.sleep(1)
        max_wait -= 1

    assert get_login_token(driver=driver) is not None
