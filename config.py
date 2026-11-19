import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv


BASE_DIR = Path(__file__).resolve().parent
load_dotenv(BASE_DIR / ".env")


@dataclass(frozen=True)
class Settings:
    bot_token: str
    admin_id: int
    database_url: str


def get_settings() -> Settings:
    bot_token = os.getenv("BOT_TOKEN", "").strip()
    admin_id_value = os.getenv("ADMIN_ID", "").strip()

    if not bot_token:
        raise ValueError("BOT_TOKEN is not configured in .env")

    if not admin_id_value:
        raise ValueError("ADMIN_ID is not configured in .env")

    try:
        admin_id = int(admin_id_value)
    except ValueError as error:
        raise ValueError("ADMIN_ID must be an integer") from error

    database_path = (BASE_DIR / "master_ryadom.db").as_posix()
    database_url = f"sqlite:///{database_path}"

    return Settings(
        bot_token=bot_token,
        admin_id=admin_id,
        database_url=database_url,
    )
