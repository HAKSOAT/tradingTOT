from abc import ABC, abstractmethod
from enum import Enum

import json
from os.path import expanduser
from typing import Optional
from pathlib import Path
from dataclasses import dataclass


DEFAULT_AUTH_DIRECTORY = Path(expanduser("~/.TOT/auth"))
DEFAULT_SCREENSHOTS_DIRECTORY = Path(expanduser("~/.TOT/shots"))


@dataclass
class AuthData:
    DUUID: str
    LoginToken: str
    UserAgent: Optional[str] = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) "
                                "Chrome/102.0.5005.63 Safari/537.36")


class ShotPath(str, Enum):
    ACCEPT_COOKIES = "accept_cookies.png",
    AFTER_LOGIN = "after_login.png",
    BEFORE_LOGIN = "before_login.png"


class Storage(ABC):
    @abstractmethod
    def read(self):
        pass

    @abstractmethod
    def write(self, data):
        pass


class LocalShotStorage(Storage):
    def __init__(self, index, shots_dir: Path = DEFAULT_SCREENSHOTS_DIRECTORY) -> None:
        self.dir = shots_dir / index
        self.dir.mkdir(parents=True, exist_ok=True)

    def read(self):
        raise NotImplementedError("Reading of images not supported.")

    def write(self, driver, type_: ShotPath):
        if not isinstance(type_, ShotPath):
            raise ValueError(f"The type: {type_} is not supported.")
        driver.save_screenshot(Path(self.dir, type_.value))

    def delete(self):
        for enum, shot_path in ShotPath.__members__.items():
            path = Path(self.dir, shot_path.value)
            if path.exists():
                path.unlink()


class LocalAuthStorage(Storage):
    def __init__(self, auth_dir: Path = DEFAULT_AUTH_DIRECTORY) -> None:
        self.dir = auth_dir
        self.dir.mkdir(parents=True, exist_ok=True)
        self.file_path = Path(self.dir) / "auth.json"

    def read(self) -> Optional[AuthData]:
        if not self.file_path.exists():
            return None

        with open(self.file_path) as handler:
            data = json.load(handler)
            expected_keys = set(AuthData.__annotations__.keys())
            data = {k: v for k, v in data.items() if k in expected_keys}
            return AuthData(**data)

    def write(self, data: AuthData) -> Path:
        with open(self.file_path, "w") as handler:
            json.dump(data.__dict__, handler)

        return self.file_path

    def delete(self):
        self.file_path.unlink()
