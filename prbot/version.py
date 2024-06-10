from pathlib import Path

import tomllib

BASE_DIR = Path(__name__).parent


def _get_app_version() -> str:
    with open(BASE_DIR / "pyproject.toml", "rb") as fd:
        pyproject_content = tomllib.load(fd)
        version = pyproject_content["tool"]["poetry"]["version"]
        return str(version)


__version__ = _get_app_version()
