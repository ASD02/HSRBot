import pytest

from hsrbot.warp_tracker import (WarpImportError, compute_history, fetch_all, normalize,
                                 parse_authkey_url)

OK = "https://webstatic.hoyoverse.com/x/?authkey_ver=1&authkey=abc%2Fd&game_biz=hkrpg_global"


def test_url_validation():
    assert parse_authkey_url(OK)["authkey"] == "abc/d"
    for bad in ["http://webstatic.hoyoverse.com/?authkey=a", "https://evil.com/?authkey=a",
                "https://hoyoverse.com.evil.com/?authkey=a", "https://nothoyoverse.com/?authkey=a",
                "https://webstatic.hoyoverse.com/?x=1", "nope"]:
        with pytest.raises(ValueError):
            parse_authkey_url(bad)


def rec(i, banner, item, rarity, time=None):
    return {"record_id": str(i), "banner": banner, "item": item, "rarity": rarity,
            "time": time or f"2026-01-01 00:00:{i:02d}"}


def test_history_pity_and_5050():
    rows = [rec(n, "character", "x", 3) for n in range(1, 4)] + [rec(4, "character", "Welt", 5)] + \
           [rec(n, "character", "y", 4) for n in range(5, 7)] + [rec(7, "character", "Seele", 5)] + \
           [rec(8, "character", "z", 3)]
    s = compute_history(rows)["character"]
    assert s["total"] == 8 and s["pity"] == 1 and s["jade"] == 8 * 160
    assert [(f["pity"], f["lost_5050"]) for f in s["fives"]] == [(4, True), (3, False)]
    assert 0 < s["luck"] < 1


def test_history_sorts_and_edge_cases():
    assert compute_history([]) == {}
    same = "2026-01-01 00:00:09"
    rows = [rec(10, "lightcone", "LC", 5, same), rec(9, "lightcone", "a", 3, same)]
    assert compute_history(rows)["lightcone"]["fives"][0]["pity"] == 2  # same time: record_id breaks the tie
    assert compute_history([rec(1, "standard", "Welt", 5)])["standard"]["luck"] is None


def test_normalize_skips_unknown_and_malformed():
    good = {"id": "1", "gacha_type": "11", "name": "A", "rank_type": "5", "time": "t"}
    assert normalize(good)["banner"] == "character"
    assert normalize({**good, "gacha_type": "99"}) is None
    assert normalize({"gacha_type": "11"}) is None


class FakeResp:
    def __init__(self, body):
        self.body = body

    async def __aenter__(self):
        return self

    async def __aexit__(self, *a):
        pass

    async def json(self, content_type=None):
        return self.body


class FakeSession:
    def __init__(self, body):
        self.body = body

    def get(self, *a, **k):
        return FakeResp(self.body)


async def test_fetch_expired_and_other_errors():
    with pytest.raises(WarpImportError, match="expired"):
        await fetch_all(FakeSession({"retcode": -101, "message": "authkey timeout"}), {})
    with pytest.raises(WarpImportError, match="boom"):
        await fetch_all(FakeSession({"retcode": -1, "message": "boom"}), {})


async def test_fetch_ok_single_page():
    body = {"retcode": 0, "data": {"list": [{"id": "1", "gacha_type": "11", "name": "A",
                                             "rank_type": "3", "time": "t"}]}}
    out = await fetch_all(FakeSession(body), {}, gacha_types=("11",))
    assert len(out) == 1 and out[0]["item"] == "A"
