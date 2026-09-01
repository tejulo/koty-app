import os
from pathlib import Path

from dotenv import dotenv_values


def environment(project_root: Path) -> dict[str, str]:
    values = dotenv_values(project_root / ".env")
    return {
        **{key: value for key, value in values.items() if value},
        **os.environ,
    }
