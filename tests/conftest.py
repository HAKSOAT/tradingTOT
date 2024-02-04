from pathlib import Path
from unittest.mock import patch
from pytest import fixture
from selenium.common.exceptions import WebDriverException

from dotenv import load_dotenv

from src.trading212 import browser_utils


@fixture(scope="function")
def test_env():
    test_folder = Path(__file__).parent.resolve()
    env_name = Path("test.env")
    load_dotenv(test_folder / env_name)


@fixture(scope="session")
def driver():
    driver = browser_utils.Driver.load()
    with patch.object(browser_utils.Driver, "load") as mock_driver:
        mock_driver.return_value = driver
        yield driver
        driver.close()


def clear_browser(driver):
    driver.delete_all_cookies()
    try:
        driver.execute_script('localStorage.clear();')
    except WebDriverException as err:
        if "storage is disabled inside 'data:'" not in err.args[0].lower():
            raise Exception("Could not clear local storage") from err