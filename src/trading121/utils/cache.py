import json
from typing import Dict, Optional
from pathlib import Path
from dataclasses import dataclass

from trading121.constants import DEFAULT_AUTH_DIRECTORY


@dataclass
class AuthData:
    DUUID: str
    LoginToken: str
    UserAgent: Optional[str] = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) "
                                "Chrome/102.0.5005.63 Safari/537.36")


class LocalAuthStorage:
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
