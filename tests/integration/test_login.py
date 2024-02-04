import os
import time

from src.trading212.browser_utils import login_trading212, get_login_token
from tests.conftest import clear_browser


TRADING212_URLS = ["https://live.trading212.com/", "https://demo.trading212.com/"]


def test_login_correct_details(driver, test_env):
    username = os.environ["TRADING212_EMAIL"]
    password = os.environ["TRADING212_PASSWORD"]

    clear_browser(driver)

    assert get_login_token(driver) is None
    driver = login_trading212(driver, username, password)

    # Waiting till the browser's page changes as the change does not happen immediately and this may lead to the
    # failure of the token extraction.
    max_wait = 5
    while max_wait or (driver.current_url not in TRADING212_URLS):
        time.sleep(1)
        max_wait -= 1

    assert get_login_token(driver) is not None


def test_buy_order_workflow():
    pass