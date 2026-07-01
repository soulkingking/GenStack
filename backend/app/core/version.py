from pathlib import Path

_REPOSITORY_ROOT = Path(__file__).resolve().parents[3]

APP_NAME = "GenStack"


def _read_version_file() -> str:
    try:
        raw_version = (_REPOSITORY_ROOT / "VERSION").read_text(encoding="utf-8").strip()
    except OSError:
        return ""
    return raw_version.splitlines()[0].strip() if raw_version else ""


# Source archives may omit VERSION, so development imports need an explicit fallback.
APP_VERSION = _read_version_file() or "0.0.0-dev"
