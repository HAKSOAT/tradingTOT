"""The Trading212 Broker package."""
from pathlib import Path

from dotenv import load_dotenv

repo_folder = Path(__file__).parent.parent.parent.resolve()
env_name = Path("local.env")

load_dotenv(repo_folder / env_name)

from .trading212 import Trading212
