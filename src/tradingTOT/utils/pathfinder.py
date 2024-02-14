import os
import platform
import subprocess

from abc import ABC, abstractmethod
from enum import Enum
from pathlib import Path
from typing import Optional


class Browser(str, Enum):
    chrome = "chrome"
    firefox = "firefox"
    edge = "edge"
    safari = "safari"


class Pathfinder(ABC):
    @abstractmethod
    def find(self, browser):
        pass


class WindowsPathfinder(Pathfinder):
    def __init__(self):
        pass

    def find(self, browser: Browser) -> Optional[Path]:
        browser_name = str(browser).lower()
        if browser == Browser.edge:
            browser_name = "msedge"
        elif browser == Browser.safari:
            raise Exception("Safari is not available on Linux.")
        elif browser not in list(Browser.__members__):
            raise Exception("Browser not supported.")

        result = subprocess.check_output(['where', browser_name], shell=True).decode().strip()
        return result.split('\r\n')[0] if result else None


class LinuxPathfinder(Pathfinder):
    def __init__(self):
        pass

    @staticmethod
    def _find_with_path(browser: Browser) -> Optional[Path]:
        paths = []
        if browser == Browser.edge:
            paths = [
                '/usr/bin/microsoft-edge',
                '/usr/bin/microsoft-edge-dev',  # If using the Developer version
            ]
        elif browser == Browser.chrome:
            paths = [
                '/usr/bin/google-chrome',
                '/usr/bin/chromium',
                '/usr/bin/chromium-browser',
            ]
        elif browser == Browser.firefox:
            paths = [
                '/usr/bin/firefox',
                '/bin/firefox',
            ]
        elif browser == Browser.safari:
            raise Exception("Safari is not available on Linux.")
        elif browser not in list(Browser.__members__):
            raise Exception("Browser not supported.")

        for path in paths:
            if os.path.isfile(path):
                return path

    @staticmethod
    def _find_with_which(browser: Browser) -> Optional[Path]:
        if browser not in list(Browser.__members__):
            raise Exception("Browser not supported.")

        result = subprocess.check_output(['which', str(browser).lower()]).decode().strip()
        return result if result else None

    def find(self, browser: Browser) -> Optional[Path]:
        path = None
        try:
            path = self._find_with_path(browser)
        except Exception as e:
            pass

        if not path:
            path = self._find_with_which(browser)

        return path


class MacPathfinder(Pathfinder):
    @staticmethod
    def _find_with_spotlight(browser: Browser) -> Optional[Path]:
        if browser not in list(Browser.__members__):
            raise Exception("Browser not supported.")
        elif browser == Browser.chrome:
            domain = "com.google.Chrome"
        elif browser == Browser.edge:
            domain = "com.microsoft.edgemac"
        elif browser == Browser.firefox:
            domain = "org.mozilla.firefox"
        else:
            return None

        result = subprocess.check_output(
            ['mdfind', f'kMDItemCFBundleIdentifier == {domain}']).decode().strip()
        return result.split('\n')[0] if result else None

    @staticmethod
    def _find_with_path(browser: Browser) -> Optional[Path]:
        if browser == Browser.chrome:
            path = '/Applications/Google Chrome.app'
        elif browser == Browser.edge:
            path = '/Applications/Microsoft Edge.app'
        elif browser == Browser.safari:
            path = '/Applications/Safari.app'
        elif browser == Browser.firefox:
            path = '/Applications/Firefox.app'
        else:
            raise Exception("Browser not supported.")

        return path if os.path.exists(path) else None

    def find(self, browser: Browser) -> Optional[Path]:
        path = None
        try:
            path = self._find_with_path(browser)
        except Exception as e:
            pass

        if not path:
            path = self._find_with_spotlight(browser)

        return path


def find_path() -> Optional[Path]:
    os_name = platform.system()
    if os_name == "Darwin":
        finder = MacPathfinder()
    elif os_name == "Linux":
        finder = LinuxPathfinder()
    elif os_name == "Windows":
        finder = WindowsPathfinder()
    else:
        raise Exception(f"OS not recognized. platform.system() returns `{os_name}` instead of Darwin, Linux or Windows.")

    for browser in Browser.__members__.values():
        if browser != Browser.safari:
            continue

        try:
            path = finder.find(browser)
            if path:
                return Path(path)
        except Exception as e:
            pass

    return None
