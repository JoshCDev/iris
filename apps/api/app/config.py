import os
from functools import lru_cache
from pathlib import Path

_REPO = Path(__file__).resolve().parents[3]

# Official DeepSeek IDs as of 21 Aug 2026 (api-docs.deepseek.com/updates).
DEFAULT_LLM_MODEL = "deepseek-v4-flash-vision-exp"


def _load_dotenv() -> None:
    """Load repo-root .env into os.environ without overriding existing keys.

    Skipped when IRIS_SKIP_DOTENV=1 (set by pytest conftest).
    """
    if os.environ.get("IRIS_SKIP_DOTENV"):
        return
    path = _REPO / ".env"
    if not path.is_file():
        return
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        key, value = key.strip(), value.strip().strip('"').strip("'")
        if key and key not in os.environ:
            os.environ[key] = value


def default_db_url() -> str:
    env = os.environ.get("IRIS_DB")
    if env:
        return env
    return f"sqlite:///{(_REPO / 'apps' / 'api' / 'storage' / 'iris.db').as_posix()}"


class Settings:
    def __init__(self) -> None:
        _load_dotenv()
        self.iris_db: str = default_db_url()
        self.iris_llm_model: str = os.environ.get("IRIS_LLM_MODEL", DEFAULT_LLM_MODEL)
        self.deepseek_api_key: str = os.environ.get("DEEPSEEK_API_KEY", "")
        # Demo mode: explicit flag (L2 auth stays stubbed while on).
        self.iris_demo_mode: bool = os.environ.get("IRIS_DEMO_MODE", "1") == "1"
        # Empty token = demo mode: auth on ingest is optional.
        self.iris_device_token: str = os.environ.get("IRIS_DEVICE_TOKEN", "")
        self.web_origin: str = os.environ.get("WEB_ORIGIN", "http://localhost:3000")
        self.lat: float = float(os.environ.get("IRIS_LAT", "-7.3305"))
        self.lon: float = float(os.environ.get("IRIS_LON", "110.5064"))
        # Kelurahan Salatiga, Kec. Sidorejo, Kota Salatiga (area_code_part2.pdf).
        self.bmkg_adm4: str = os.environ.get("BMKG_ADM4", "33.73.01.1003")
        self.bmkg_api_key: str = os.environ.get("BMKG_API_KEY", "")
        self.bmkg_timeout_s: float = float(
            os.environ.get("BMKG_TIMEOUT_S", "20.0"))


@lru_cache
def get_settings() -> Settings:
    return Settings()


def reset_settings_cache() -> None:
    get_settings.cache_clear()
