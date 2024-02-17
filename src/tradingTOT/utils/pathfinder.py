import os
import platform
import subprocess

from abc import ABC, abstractmethod
from enum import Enum
from pathlib import Path
from typing import Optional, List


class Browser(str, Enum):
    chrome = "chrome"
    edge = "edge"
    safari = "safari"


class Pathfinder(ABC):
    @abstractmethod
    def find(self, browser):
        pass


class WindowsPathfinder(Pathfinder):
    def __init__(self):
        pass

    def _get_paths(self, browser: Browser) -> List[Path]:
        if browser == Browser.edge:
            paths = [
                # Stable
                Path(os.environ['PROGRAMFILES(X86)'], 'Microsoft', 'Edge', 'Application', 'msedge.exe'),
                Path(os.environ['PROGRAMFILES'], 'Microsoft', 'Edge', 'Application', 'msedge.exe'),
                # Beta
                Path(os.environ['PROGRAMFILES(X86)'], 'Microsoft', 'Edge Beta', 'Application', 'msedge.exe'),
                Path(os.environ['PROGRAMFILES'], 'Microsoft', 'Edge Beta', 'Application', 'msedge.exe'),
                # Dev
                Path(os.environ['PROGRAMFILES(X86)'], 'Microsoft', 'Edge Dev', 'Application', 'msedge.exe'),
                Path(os.environ['PROGRAMFILES'], 'Microsoft', 'Edge Dev', 'Application', 'msedge.exe'),
                # Canary
                Path(os.environ['PROGRAMFILES(X86)'], 'Microsoft', 'Edge SxS', 'Application', 'msedge.exe'),
                Path(os.environ['PROGRAMFILES'], 'Microsoft', 'Edge SxS', 'Application', 'msedge.exe'),
                # Edge WebView (for developers, might not be needed for general users but included for completeness)
                Path(os.environ['PROGRAMFILES(X86)'], 'Microsoft', 'EdgeWebView', 'Application',
                             'msedgewebview2.exe'),
                Path(os.environ['PROGRAMFILES'], 'Microsoft', 'EdgeWebView', 'Application',
                             'msedgewebview2.exe'),
            ]
        elif browser == Browser.chrome:
            paths = [
                Path(os.environ['PROGRAMFILES(X86)'], 'Google', 'Chrome', 'Application', 'chrome.exe'),
                Path(os.environ['PROGRAMFILES'], 'Google', 'Chrome', 'Application', 'chrome.exe'),
                Path(os.environ['LOCALAPPDATA'], 'Google', 'Chrome', 'Application', 'chrome.exe'),
                # Beta
                Path(os.environ['PROGRAMFILES(X86)'], 'Google', 'Chrome Beta', 'Application', 'chrome.exe'),
                Path(os.environ['PROGRAMFILES'], 'Google', 'Chrome Beta', 'Application', 'chrome.exe'),
                # Dev
                Path(os.environ['PROGRAMFILES(X86)'], 'Google', 'Chrome Dev', 'Application', 'chrome.exe'),
                Path(os.environ['PROGRAMFILES'], 'Google', 'Chrome Dev', 'Application', 'chrome.exe'),
                # Canary
                Path(os.environ['PROGRAMFILES(X86)'], 'Google', 'Chrome SxS', 'Application', 'chrome.exe'),
                Path(os.environ['PROGRAMFILES'], 'Google', 'Chrome SxS', 'Application', 'chrome.exe'),
            ]
        elif browser == Browser.safari:
            return []
        elif browser not in list(Browser.__members__):
            raise Exception("Browser not supported.")

        return paths

    def _find_with_path(self, browser: Browser) -> Optional[Path]:
        paths = self._get_paths(browser)
        for path in paths:
            if os.path.isfile(path):
                return path

    def find(self, browser: Browser) -> Optional[Path]:
        path = None
        try:
            path = self._find_with_path(browser)
        except Exception as e:
            print(e)

        return path


class LinuxPathfinder(Pathfinder):
    def __init__(self):
        pass

    def _get_paths(self, browser: Browser) -> List[Path]:
        if browser == Browser.edge:
            paths = [
                Path('/usr/bin/microsoft-edge'),
                Path('/usr/bin/microsoft-edge-dev'),  # If using the Developer version
            ]
        elif browser == Browser.chrome:
            paths = [
                Path('/usr/bin/google-chrome'),
                Path('/usr/bin/google-chrome-stable'),
                Path('/usr/bin/chromium'),
                Path('/usr/bin/chromium-browser'),
            ]
        elif browser == Browser.safari:
            return []
        elif browser not in list(Browser.__members__):
            raise Exception("Browser not supported.")

        return paths


    def _find_with_path(self, browser: Browser) -> Optional[Path]:
        paths = self._get_paths(browser)
        for path in paths:
            if os.path.isfile(path):
                return path

    def _find_with_which(self, browser: Browser) -> Optional[Path]:
        paths = self._get_paths(browser)

        for path in paths:
            command = ['which', path.name.lower()]
            result = subprocess.check_output(command).decode().strip()
            if result:
                return result


    def find(self, browser: Browser) -> Optional[Path]:
        path = None
        try:
            path = self._find_with_path(browser)
        except Exception as e:
            print(e)

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
        else:
            raise Exception("Browser not supported.")

        return path if os.path.exists(path) else None

    def find(self, browser: Browser) -> Optional[Path]:
        path = None
        try:
            path = self._find_with_path(browser)
        except Exception as e:
            print(e)

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
        try:
            path = finder.find(browser)
            if path:
                return Path(path)
        except Exception as e:
            print(e)

    return None
