"""Enka.Network HSR showcase client. The player's in-game showcase must be public."""
import asyncio
import time
from dataclasses import dataclass, field

URL = "https://enka.network/api/hsr/uid/{uid}"
UA = "HSRBot/0.1 (discord bot)"
_ERRORS = {
    400: "That UID is malformed.",
    404: "No player with that UID.",
    424: "The game is under maintenance; try again later.",
    429: "Rate limited by Enka. Try again in a minute.",
    500: "Enka had a server error. Try again later.",
    503: "Enka is unavailable right now.",
}


class EnkaError(Exception):
    pass


@dataclass
class Profile:
    uid: str
    nickname: str
    level: int
    world_level: int
    achievements: int | None
    characters: int | None
    avatars: list = field(default_factory=list)  # raw avatarDetailList entries
    ttl: int = 60


def parse_profile(payload) -> Profile:
    try:
        d = payload["detailInfo"]
        rec = d.get("recordInfo") or {}
        return Profile(
            uid=str(d.get("uid") or payload.get("uid")), nickname=str(d.get("nickname", "?")),
            level=int(d.get("level", 0)), world_level=int(d.get("worldLevel", 0)),
            achievements=rec.get("achievementCount"), characters=rec.get("avatarCount"),
            avatars=[a for a in d.get("avatarDetailList") or [] if isinstance(a, dict)],
            ttl=max(int(payload.get("ttl", 60)), 60))
    except (KeyError, TypeError, ValueError, AttributeError):
        raise EnkaError("Enka returned data I couldn't read.") from None


_cache: dict[str, tuple[float, Profile]] = {}
_sem = asyncio.Semaphore(2)


async def fetch_profile(session, uid: str) -> Profile:
    hit = _cache.get(uid)
    if hit and hit[0] > time.monotonic():
        return hit[1]
    async with _sem:
        try:
            async with session.get(URL.format(uid=uid), headers={"User-Agent": UA}, timeout=20) as r:
                if r.status != 200:
                    raise EnkaError(_ERRORS.get(r.status, f"Enka returned HTTP {r.status}."))
                payload = await r.json(content_type=None)
        except EnkaError:
            raise
        except Exception:
            raise EnkaError("Couldn't reach Enka.") from None
    prof = parse_profile(payload)
    _cache[uid] = (time.monotonic() + prof.ttl, prof)
    return prof
