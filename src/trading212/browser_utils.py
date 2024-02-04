import os
import time
from typing import Dict, Callable, Union

import requests
from requests.exceptions import ConnectionError
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.webdriver import WebDriver
from selenium.common.exceptions import TimeoutException, NoSuchElementException
from selenium_stealth import stealth
from webdriver_manager.chrome import ChromeDriverManager
from webdriver_manager.core.utils import ChromeType

from .exceptions import AuthError
from .endpoints import HOME_URL, AUTHENTICATE_URL


class Driver:
    driver = None

    @classmethod
    def load(cls) -> WebDriver:
        """Create a headless driver with needed properties to load Trading212.

        Returns:
            Selenium Webdriver
        """
        if cls.driver:
            return cls.driver

        options = webdriver.ChromeOptions()
        # export CHROME_VERSION="114.0.5735.90" && wget --no-verbose -O /tmp/chrome.deb https://dl.google.com/linux/chrome/deb/pool/main/g/google-chrome-stable/google-chrome-stable_${CHROME_VERSION}-1_amd64.deb && apt install -y /tmp/chrome.deb && rm /tmp/chrome.deb
        options.binary_location = "/usr/bin/google-chrome-stable"
        options.add_argument('--no-sandbox')
        options.add_argument('--disable-dev-shm-usage')
        options.add_argument("--disable-extensions")
        options.add_argument("--headless")
        options.add_experimental_option("excludeSwitches", ["enable-automation"])
        options.add_experimental_option('useAutomationExtension', False)

        driver_path = ChromeDriverManager(chrome_type=ChromeType.CHROMIUM, version="114.0.5735.90").install()
        driver = webdriver.Chrome(driver_path, options=options)
        stealth(driver,
            languages=["en-US", "en"],
            vendor="Google Inc.",
            platform="Win32",
            webgl_vendor="Intel Inc.",
            renderer="Intel Iris OpenGL Engine",
            fix_hairline=True,
        )
        scale = 2
        width = 1920
        height = 1080
        driver.set_window_size(width * scale, height * scale)

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
    driver.get(HOME_URL)
    accept_cookies(driver)

    login_link = driver.find_element(By.XPATH, "//p[starts-with(@class, 'Header_login-button')]")
    login_link.click()
    email_input = driver.find_element(By.XPATH, "//input[@name='email' and @type='email']")
    email_input.send_keys(email)
    password_input = driver.find_element(By.XPATH, "//input[@name='password' and @type='password']")
    password_input.send_keys(password)
    login_button = driver.find_element(By.XPATH, "//input[@type='submit' and @value='Log in']")
    login_button.click()
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
    for trials in range(10):
        duuid = get_duuid(driver)
        if duuid:
            break
        time.sleep(3)
    else:
        print(driver.page_source)
        print(driver)
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
    def wrapper(*args, **kwargs):
        if not args and not kwargs:
            raise Exception("The wrapped function needs at least one argument.")

        instance = kwargs.get("self", args[0])

        try:
            auth_response = instance.session.get(AUTHENTICATE_URL)
            is_auth = True if auth_response.status_code == 200 else False
        except ConnectionError:
            is_auth = False

        while not is_auth:
            driver = Driver.load()
            driver = login_trading212(driver, os.environ.get("TRADING212_EMAIL"),
                                      os.environ.get("TRADING212_PASSWORD"))
            headers = generate_headers(driver)
            auth_cookies = {'LOGIN_TOKEN': get_login_token(driver)}
            driver.close()
            session = requests.Session()
            session.headers.update(headers)
            session.cookies.update(auth_cookies)
            instance.session = session

            auth_response = instance.session.get(AUTHENTICATE_URL)
            is_auth = True if auth_response.status_code == 200 else False

        if kwargs.get("self"):
            kwargs["self"] = instance
        else:
            args = list(args)
            args[0] = instance
            args = tuple(args)

        return func(*args, **kwargs)

    return wrapper
