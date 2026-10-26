"""Game data (characters, light cones) from the community StarRailRes dataset, cached locally."""
import json
import logging
import time
from pathlib import Path

log = logging.getLogger("hsrbot.data")

BASE = "https://raw.githubusercontent.com/Mar-7th/StarRailRes/master/index_min/en/"
FILES = {"characters": "characters.json", "light_cones": "light_cones.json"}
MAX_AGE = 7 * 24 * 3600


class GameData:
    def __init__(self, data_dir):
        self.cache_dir = Path(data_dir) / "cache"
        self.characters: dict[str, dict] = {}
        self.light_cones: dict[str, dict] = {}

    @classmethod
    def from_dicts(cls, characters: dict, light_cones: dict) -> "GameData":
        gd = cls(".")
        gd.characters, gd.light_cones = characters, light_cones
        return gd

    async def load(self, session, force: bool = False) -> None:
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        for attr, fname in FILES.items():
            path = self.cache_dir / fname
            stale = not path.exists() or time.time() - path.stat().st_mtime > MAX_AGE
            if force or stale:
                try:
                    async with session.get(BASE + fname, timeout=20) as r:
                        r.raise_for_status()
                        path.write_text(await r.text(), encoding="utf-8")
                except Exception as e:  # keep serving stale cache if offline
                    log.warning("could not refresh %s: %s", fname, e)
            if path.exists():
                try:
                    setattr(self, attr, json.loads(path.read_text(encoding="utf-8")))
                except json.JSONDecodeError:
                    log.warning("corrupt cache %s", path)

    def search(self, kind: str, query: str, limit: int = 25) -> list[dict]:
        items = list((self.characters if kind == "character" else self.light_cones).values())
        q = query.strip().lower()[:100]
        if not q:
            return sorted(items, key=lambda i: i.get("name", ""))[:limit]
        pre = [i for i in items if i.get("name", "").lower().startswith(q)]
        sub = [i for i in items if q in i.get("name", "").lower() and i not in pre]
        return (sorted(pre, key=lambda i: i["name"]) + sorted(sub, key=lambda i: i["name"]))[:limit]

    def get(self, kind: str, name: str) -> dict | None:
        for i in self.search(kind, name, 100):
            if i.get("name", "").lower() == name.strip().lower():
                return i
        return None
