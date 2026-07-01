"""Session logging configuration."""

from pathlib import Path

from pydantic_settings import BaseSettings


class SessionLogSettings(BaseSettings):
    enabled: bool = True
    excel_path: str = "logs/session_logs.xlsx"
    max_cell_length: int = 32000

    class Config:
        env_prefix = "SESSION_LOG_"


settings = SessionLogSettings()


def resolve_log_path() -> Path:
    path = Path(settings.excel_path)
    if not path.is_absolute():
        path = Path(__file__).resolve().parent.parent / path
    path.parent.mkdir(parents=True, exist_ok=True)
    return path
