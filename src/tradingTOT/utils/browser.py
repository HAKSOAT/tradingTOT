from __future__ import annotations

import logging
import os
import re
from datetime import datetime
from dataclasses import dataclass
from pathlib import Path
from functools import wraps
from typing import Dict, Callable, Union, Optional, Type

import requests
from requests.exceptions import ConnectionError
from selenium import webdriver
from selenium.common.exceptions import TimeoutException, NoSuchElementException, WebDriverException
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.webdriver import WebDriver
from selenium.webdriver.remote.webdriver import WebDriver as RemoteWebDriver
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.common.options import ArgOptions
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait
from selenium_stealth import stealth
from tenacity import retry, stop_after_attempt

from tradingTOT.enums import Environment
from tradingTOT.exceptions import AuthError
from tradingTOT.endpoints import HOME_URL, AUTHENTICATE_URL
from tradingTOT.utils.storage import AuthData, LocalAuthStorage, ShotPath, LocalShotStorage
from tradingTOT.utils.pathfinder import find_path, Browser


# TODO: Silence the INFO logs that show when using Edge browser.
logger: Final = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)

@dataclass
class DriverClassPack:
    driver: Type[RemoteWebDriver] = webdriver.Chrome
    options: Type[ArgOptions] = webdriver.ChromeOptions

    @staticmethod
    def get(browser_path: Union[Path, str]) -> DriverClassPack:
        if Browser.edge.lower() in str(browser_path):
            return DriverClassPack(driver=webdriver.Edge, options=webdriver.EdgeOptions)
        elif Browser.safari.lower() in str(browser_path):
            return DriverClassPack(driver=webdriver.Safari, options=webdriver.SafariOptions)
        else:
            return DriverClassPack()


class Driver:
    driver = None

    @classmethod
    def load(cls, force_new=False) -> WebDriver:
        """Create a headless driver with needed properties to load Trading212.

        Returns:
            Selenium Webdriver
        """
        if force_new:
            if isinstance(cls.driver, WebDriver):
                cls.driver.quit()
                cls.driver = None

        if cls.driver:
            return cls.driver

        # export CHROME_VERSION="114.0.5735.90" && wget --no-verbose -O /tmp/chrome.deb https://dl.google.com/linux/chrome/deb/pool/main/g/google-chrome-stable/google-chrome-stable_${CHROME_VERSION}-1_amd64.deb && apt install -y /tmp/chrome.deb && rm /tmp/chrome.deb
        binary_location = os.environ.get("BINARY_PATH")
        if not binary_location:
            path = find_path()
            if not path:
                raise FileNotFoundError("No browser binary was found. "
                                        "Ensure that one of Chrome, Firefox, MS Edge or Safari is installed. "
                                        "If you are certain they are installed, set the `BINARY_PATH` environment variable. "
                                        "Check the docs for more information.")

            binary_location = str(path.resolve())

        class_pack = DriverClassPack.get(binary_location)
        options = class_pack.options()
        options.binary_location = binary_location
        options.add_argument(
            f'user-agent={AuthData.UserAgent}'
        )
        scale = 2
        width = 1680
        height = 1050
        options.add_argument(f"--window-size={width * scale},{height * scale}")
        options.add_argument('--disable-dev-shm-usage')
        options.add_argument("--disable-extensions")
        options.add_argument("--headless")

        if hasattr(options, "add_experimental_option"):
            options.add_experimental_option("excludeSwitches", ["enable-automation"])
            options.add_experimental_option('useAutomationExtension', False)

        driver = class_pack.driver(options=options)
        # Stealth only works for Chrome.
        if class_pack.driver == webdriver.Chrome:
            stealth(
                driver, languages=["en-US", "en"], vendor="Google Inc.",
                platform="Win32", webgl_vendor="Intel Inc.", renderer="Intel Iris OpenGL Engine",
                fix_hairline=True,
            )

        cls.driver = driver
        return driver


def accept_cookies(driver: WebDriver) -> None:
    """Click on the accept cookies button in the page loaded by the driver.

    Args:
        driver: Selenium Webdriver

    Returns:
    """
    try:
        accept_button = driver.find_element(By.XPATH, "//p[text()='Accept all cookies']")
        accept_button.click()
    except NoSuchElementException:
        try:
            login_nav_xpath = "//p[starts-with(@class, 'Header_login-button')]"
            max_wait_time = 3
            WebDriverWait(driver, max_wait_time).until(
                EC.element_to_be_clickable((By.XPATH, login_nav_xpath))
            )
        except TimeoutException:
            raise AuthError("Unable to accept cookies")


def log_attempt_number(retry_state):
    """return the result of the last call attempt"""
    logger.warn(f"Retrying login attempt: {retry_state.attempt_number}...")


# Retrying because Trading212 sometimes comes up with a "something went wrong" error.
@retry(stop=stop_after_attempt(3), after=log_attempt_number)
def login_tradingTOT(driver: WebDriver, email: str, password: str) -> WebDriver:
    """
    Login to a Trading212 account.

    Args:
        driver: Selenium Webdriver
        email: Trading212 Email
        password: Trading212 Password

    Returns:
        Selenium Webdriver
    """
    shot_storage = LocalShotStorage(datetime.now().strftime("%m-%d-%Y_%H-%M-%S"))

    retries = 3
    while retries:
        retries -= 1
        try:
            driver.get(HOME_URL)
            break
        except WebDriverException as err:
            # Sometimes the browser becomes inaccessible, especially after long periods of non-use.
            if "disconnected: not connected to devtools" in err.msg.lower():
                driver = Driver.load(force_new=True)
            else:
                raise AuthError("Failed to load home page.") from err

    env_pattern = "|".join([e for e in Environment])
    if re.search(env_pattern, driver.current_url):
        print("Already logged in.")
        return driver

    shot_storage.write(driver, ShotPath.ACCEPT_COOKIES)
    accept_cookies(driver)

    actions = ActionChains(driver)
    login_link = driver.find_element(By.XPATH, "//p[starts-with(@class, 'Header_login-button')]")
    actions.move_to_element(login_link).click(login_link).perform()

    actions = ActionChains(driver)
    email_xpath = "//input[@type='email']"

    # The check below confirms page loaded fully. Wait time set based on observation.
    max_wait_time = 30
    try:
        WebDriverWait(driver, max_wait_time).until(
            EC.presence_of_element_located(
                (By.XPATH, email_xpath)
            )
        )
    except TimeoutException as err:
        raise AuthError(f"Email element not found using xpath: {email_xpath} after waiting {max_wait_time} seconds.") from err
    finally:
        shot_storage.write(driver, ShotPath.BEFORE_LOGIN)

    email_input = driver.find_element(By.XPATH, email_xpath)
    actions.move_to_element(email_input).click(email_input).send_keys(email).pause(0.1)

    password_input = driver.find_element(By.XPATH, "//input[@type='password']")
    actions.move_to_element(password_input).click(password_input).send_keys(password).pause(0.1)

    login_button = driver.find_element(By.XPATH, '//div[text()="Log in"]')
    actions.move_to_element(login_button).click(login_button).pause(0.1)

    actions.perform()

    # The check below confirms page loaded fully. Wait time set based on observation.
    try:
        WebDriverWait(driver, max_wait_time).until(
            EC.presence_of_element_located(
                (By.XPATH, "//div[@data-testid='tab-button-home-open']")
            )
        )
    except TimeoutException as err:
        raise AuthError(f"Trading dashboard failed to load in {max_wait_time} seconds.") from err
    finally:
        shot_storage.write(driver, ShotPath.AFTER_LOGIN)

    return driver


def get_duuid(driver: WebDriver) -> str:
    """
    Extract the duuid from cookies provided by Trading212.

    Args:
        driver: Selenium Webdriver

    Returns:
    """
    for cookie in driver.get_cookies():
        if cookie["name"].startswith("amp_"):
            # The value is a combination of various characters separated by a fullstop.
            # Only the first section of the characters is the duuid.
            return cookie["value"].split(".")[0]


def generate_headers(*, driver: Optional[WebDriver] = None, auth_data: Optional[AuthData] = None) -> Dict:
    """Get the headers needed for creating a Trading212 session.

    Args:
        driver: Selenium Webdriver
        auth_data: AuthData

    Returns:
    """
    if all([driver, auth_data]) or not any([driver, auth_data]):
        raise ValueError("Provide one of driver or auth_data.")

    if driver:
        duuid = get_duuid(driver)
        if not duuid:
            raise AuthError("DDUID Not Found")
        user_agent = driver.execute_script("return navigator.userAgent;")
    else:
        duuid = auth_data.DUUID
        user_agent = auth_data.UserAgent

    headers = {
        "User-Agent": user_agent,
        "X-Trader-Client": f"application=WC4, version=1.0.0, dUUID={duuid}",
        "Content-Type": "application/json"
    }
    return headers


def get_login_token(*, driver: Optional[WebDriver] = None, auth_data: Optional[AuthData] = None) -> Union[str, None]:
    """
    Extracts the login token from the browser cookies or auth data.

    Args:
        driver: Selenium Webdriver
        auth_data: AuthData

    Returns:
        The login token (if found) or None.
    """
    if all([driver, auth_data]) or not any([driver, auth_data]):
        raise ValueError("Provide one of driver or auth_data.")

    if driver:
        login_cookie = driver.get_cookie("LOGIN_TOKEN")
        if login_cookie:
            return login_cookie["value"]
        return None
    else:
        return auth_data.LoginToken


def enforce_auth(func: Callable):
    """Decorator that ensures successful authentication into Trading212 before the passed in callable is executed.

    Args:
        func: The function to be wrapped.

    Returns:
        A wrapper function.
    """
    @wraps(func)
    def wrapper(*args, **kwargs):
        if not args and not kwargs:
            raise ValueError("The wrapped function needs at least one argument.")

        instance = kwargs.get("self", args[0])

        try:
            auth_response = instance.session.get(AUTHENTICATE_URL)
            is_auth = True if auth_response.status_code == 200 else False
        except ConnectionError:
            is_auth = False

        # TODO: Make it possible to turn off LocalAuthStorage
        # TODO: Log when localstorage is being used and when browser is being used.
        local_auth_storage = LocalAuthStorage()

        retries = 3
        while not is_auth and retries:
            retries -= 1

            auth_data = local_auth_storage.read()
            if auth_data is None:
                driver = Driver.load()
                driver = login_tradingTOT(driver, os.environ.get("TRADINGTOT_EMAIL"),
                                          os.environ.get("TRADINGTOT_PASSWORD"))
            else:
                driver = None

            try:
                headers = generate_headers(driver=driver, auth_data=auth_data)
                auth_cookies = {'LOGIN_TOKEN': get_login_token(driver=driver, auth_data=auth_data)}
            except AuthError as err:
                if retries:
                    continue
                else:
                    raise err

            session = requests.Session()
            session.headers.update(headers)
            session.cookies.update(auth_cookies)

            instance.session = session
            auth_response = instance.session.get(AUTHENTICATE_URL)
            is_auth = True if auth_response.status_code == 200 else False

            if is_auth and auth_data is None:
                auth_data = AuthData(
                    DUUID=get_duuid(driver),
                    UserAgent=headers["User-Agent"],
                    LoginToken=auth_cookies["LOGIN_TOKEN"]
                )
                local_auth_storage.write(auth_data)
            elif not is_auth and auth_data is not None:
                local_auth_storage.delete()

        if not is_auth and not retries:
            raise AuthError("Failed to log in using Selenium.")

        if kwargs.get("self"):
            kwargs["self"] = instance
        else:
            args = list(args)
            args[0] = instance
            args = tuple(args)

        return func(*args, **kwargs)

    return wrapper
