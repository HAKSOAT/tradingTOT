import os
import re
from pathlib import Path
from functools import wraps
from typing import Dict, Callable, Union

import requests
from requests.exceptions import ConnectionError
from selenium import webdriver
from selenium.common.exceptions import TimeoutException, NoSuchElementException, WebDriverException
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.webdriver import WebDriver
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait
from selenium_stealth import stealth

from trading121.enums import Environment
from trading121.exceptions import AuthError
from trading121.endpoints import HOME_URL, AUTHENTICATE_URL


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

        options = webdriver.ChromeOptions()

        # export CHROME_VERSION="114.0.5735.90" && wget --no-verbose -O /tmp/chrome.deb https://dl.google.com/linux/chrome/deb/pool/main/g/google-chrome-stable/google-chrome-stable_${CHROME_VERSION}-1_amd64.deb && apt install -y /tmp/chrome.deb && rm /tmp/chrome.deb
        # TODO: Extract binary location to env file
        options.binary_location = "/Applications/Chromium.app/Contents/MacOS/Chromium"
        options.add_argument(
            'user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) '
            'Chrome/102.0.5005.63 Safari/537.36'
        )
        scale = 2
        width = 1680
        height = 1050
        options.add_argument(f"--window-size={width * scale},{height * scale}")
        options.add_argument('--disable-dev-shm-usage')
        options.add_argument("--disable-extensions")
        options.add_argument("--headless")
        options.add_experimental_option("excludeSwitches", ["enable-automation"])
        options.add_experimental_option('useAutomationExtension', False)

        driver = webdriver.Chrome(options=options)
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
        accept_cookies = driver.find_element(By.XPATH, "//p[text()='Accept all cookies']")
        accept_cookies.click()
    except (TimeoutException, NoSuchElementException):
        raise AuthError("Unable to accept cookies")


def login_trading212(driver: WebDriver, email: str, password: str) -> WebDriver:
    """
    Login to a Trading212 account.

    Args:
        driver: Selenium Webdriver
        email: Trading212 Email
        password: Trading212 Password

    Returns:
        Selenium Webdriver
    """
    retries = 5
    while retries:
        retries -= 1
        try:
            driver.get(HOME_URL)
            break
        except WebDriverException as err:
            if "disconnected: not connected to devtools" in err.msg.lower():
                driver = Driver.load(force_new=True)
            else:
                raise AuthError("Failed to load home page.") from err

    # TODO: Switch this to a screenshot logging functionality
    before_login_shot = Path("before_shot.png")
    driver.save_screenshot(before_login_shot)

    env_pattern = "|".join([e for e in Environment])
    if re.search(env_pattern, driver.current_url):
        print("Already logged in.")
        return driver

    accept_cookies(driver)

    actions = ActionChains(driver)

    login_link = driver.find_element(By.XPATH, "//p[starts-with(@class, 'Header_login-button')]")
    actions.move_to_element(login_link).click(login_link).perform()

    actions = ActionChains(driver)
    email_input = driver.find_element(By.XPATH, "//input[@name='email' and @type='email']")
    actions.move_to_element(email_input).click(email_input).send_keys(email).pause(0.5)

    password_input = driver.find_element(By.XPATH, "//input[@name='password' and @type='password']")
    actions.move_to_element(password_input).click(password_input).send_keys(password).pause(0.5)

    login_button = driver.find_element(By.XPATH, "//input[@type='submit' and @value='Log in']")
    actions.move_to_element(login_button).click(login_button).pause(0.5)

    actions.perform()

    # The check below confirms page loaded fully. Wait time set based on observation.
    max_wait_time = 30
    try:
        WebDriverWait(driver, max_wait_time).until(
            EC.presence_of_element_located(
                (By.XPATH, "//span[@class='account-status-header-label' and contains(text(), 'Account value')]")
            )
        )
    except TimeoutException as err:
        raise AuthError(f"Trading dashboard failed to load in {max_wait_time} seconds.") from err
    finally:
        after_login_shot = Path("after_shot.png")
        driver.save_screenshot(after_login_shot)

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


def generate_headers(driver: WebDriver) -> Dict:
    """Get the headers needed for creating a Trading212 session.

    Args:
        driver: Selenium Webdriver

    Returns:
    """
    for trials in range(5):
        duuid = get_duuid(driver)
        if duuid:
            break
    else:
        raise Exception("DDUID Not Found")

    headers = {
        "User-Agent": driver.execute_script("return navigator.userAgent;"),
        "X-Trader-Client": f"application=WC4, version=1.0.0, dUUID={duuid}",
        "Content-Type": "application/json"
    }
    return headers


def get_login_token(driver: WebDriver) -> Union[str, None]:
    """
    Extracts the login token from the browser cookies.

    Args:
        driver: Selenium Webdriver

    Returns:
        The login token (if found) or None.
    """
    login_cookie = driver.get_cookie("LOGIN_TOKEN")
    if login_cookie:
        return login_cookie["value"]
    return None


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
            raise Exception("The wrapped function needs at least one argument.")

        instance = kwargs.get("self", args[0])

        try:
            auth_response = instance.session.get(AUTHENTICATE_URL)
            is_auth = True if auth_response.status_code == 200 else False
        except ConnectionError:
            is_auth = False

        retries = 5
        while not is_auth:
            driver = Driver.load()
            driver = login_trading212(driver, os.environ.get("TRADING212_EMAIL"),
                                      os.environ.get("TRADING212_PASSWORD"))

            headers = generate_headers(driver)
            auth_cookies = {'LOGIN_TOKEN': get_login_token(driver)}
            session = requests.Session()
            session.headers.update(headers)
            session.cookies.update(auth_cookies)
            instance.session = session
            auth_response = instance.session.get(AUTHENTICATE_URL)
            is_auth = True if auth_response.status_code == 200 else False

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
