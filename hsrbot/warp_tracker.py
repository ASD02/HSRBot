"""Import and analyse Warp history from the in-game history link. Never log the URL: it holds an authkey."""
import asyncio
from collections import defaultdict
from statistics import mean
from urllib.parse import parse_qs, urlparse

from .gacha import BANNERS, pity_cdf

API = "https://public-operation-hkrpg-sg.hoyoverse.com/common/gacha_record/api/getGachaLog"
BANNER_TYPES = {"11": "character", "12": "lightcone", "1": "standard", "2": "departure",
                "21": "collab_character", "22": "collab_lightcone"}
STANDARD_5_CHARS = {"Himeko", "Welt", "Bronya", "Gepard", "Clara", "Yanqing", "Bailu"}
JADE_PER_PULL = 160
MAX_PAGES = 200


class WarpImportError(Exception):
    pass


def parse_authkey_url(url: str) -> dict:
    u = urlparse(url.strip())
    host = u.hostname or ""
    if u.scheme != "https" or not any(host == d or host.endswith("." + d) for d in ("hoyoverse.com", "mihoyo.com")):
        raise ValueError("That isn't a HoYoverse warp history link.")
    q = {k: v[0] for k, v in parse_qs(u.query).items() if v}
    if not q.get("authkey"):
        raise ValueError("The link has no authkey. Copy the full link from the in-game Warp History page.")
    return {"authkey": q["authkey"], "authkey_ver": q.get("authkey_ver", "1"),
            "sign_type": q.get("sign_type", "2"), "game_biz": q.get("game_biz", "hkrpg_global"),
            "lang": q.get("lang", "en"), "region": q.get("region", "prod_official_asia")}


def normalize(r: dict) -> dict | None:
    banner = BANNER_TYPES.get(str(r.get("gacha_type")))
    try:
        return {"record_id": str(r["id"]), "banner": banner, "item": r["name"],
                "rarity": int(r["rank_type"]), "time": r["time"]} if banner else None
    except (KeyError, TypeError, ValueError):
        return None


async def fetch_all(session, params: dict, gacha_types=tuple(BANNER_TYPES)) -> list[dict]:
    out = []
    for gt in gacha_types:
        end_id = "0"
        for _ in range(MAX_PAGES):
            q = {**params, "gacha_type": gt, "default_gacha_type": gt, "size": 20, "page": 1, "end_id": end_id}
            try:
                async with session.get(API, params=q, timeout=20) as resp:
                    body = await resp.json(content_type=None)
            except Exception:
                raise WarpImportError("Couldn't reach HoYoverse. Try again later.") from None
            code = body.get("retcode") if isinstance(body, dict) else None
            if code == -101:
                raise WarpImportError("The link expired. Reopen Warp History in game and copy a fresh link.")
            if code != 0:
                raise WarpImportError(str(body.get("message", "HoYoverse rejected the request"))
                                      if isinstance(body, dict) else "Unexpected response from HoYoverse.")
            page = (body.get("data") or {}).get("list") or []
            out += [n for r in page if (n := normalize(r))]
            if len(page) < 20:
                break
            end_id = str(page[-1]["id"])
            await asyncio.sleep(0.4)
    return out


def compute_history(rows) -> dict:
    """rows: dicts with record_id, banner, item, rarity, time. Returns {banner: stats}."""
    by = defaultdict(list)
    for r in rows:
        by[r["banner"]].append(r)
    out = {}
    for banner, recs in by.items():
        recs.sort(key=lambda r: (r["time"], int(r["record_id"])))
        count, fives = 0, []
        for r in recs:
            count += 1
            if r["rarity"] == 5:
                fives.append({"item": r["item"], "pity": count, "time": r["time"],
                              "lost_5050": banner.endswith("character") and r["item"] in STANDARD_5_CHARS})
                count = 0
        luck = None
        if banner in BANNERS and fives:
            luck = 1 - mean(pity_cdf(BANNERS[banner], f["pity"]) for f in fives)
        out[banner] = {"total": len(recs), "pity": count, "fives": fives,
                       "jade": len(recs) * JADE_PER_PULL, "luck": luck}
    return out
