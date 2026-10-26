import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv


@dataclass(frozen=True)
class Config:
    token: str
    db_path: Path
    data_dir: Path
    fernet_key: str | None
    dev_guild: int | None

    @classmethod
    def load(cls) -> "Config":
        load_dotenv()
        token = os.environ.get("DISCORD_TOKEN")
        if not token:
            raise SystemExit("DISCORD_TOKEN is not set. Copy .env.example to .env and fill it in.")
        dev = os.environ.get("DEV_GUILD_ID")
        return cls(
            token=token,
            db_path=Path(os.environ.get("DB_PATH", "hsrbot.db")),
            data_dir=Path(os.environ.get("DATA_DIR", "data")),
            fernet_key=os.environ.get("FERNET_KEY") or None,
            dev_guild=int(dev) if dev else None,
        )
