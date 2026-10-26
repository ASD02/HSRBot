import pytest

from hsrbot.config import Config
from hsrbot.db import Database


async def test_db_roundtrip_and_markers(tmp_path):
    db = Database(tmp_path / "t.db")
    await db.connect()
    await db.set_conf(1, "k", "a")
    await db.set_conf(1, "k", "b")
    assert await db.get_conf(1, "k") == "b"
    assert await db.mark_sent("x") is True
    assert await db.mark_sent("x") is False
    await db.close()


def test_config_requires_token(monkeypatch):
    monkeypatch.delenv("DISCORD_TOKEN", raising=False)
    monkeypatch.setattr("hsrbot.config.load_dotenv", lambda: None)
    with pytest.raises(SystemExit):
        Config.load()
