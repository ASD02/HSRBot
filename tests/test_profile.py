import pytest

from hsrbot.cogs.profile import rank_rows
from hsrbot.enka import EnkaError, parse_profile
from hsrbot.relics import affix_property, relic_subs, score_relic, weights_for

SUB = {"5": {"affixes": {"4": {"property": "HPAddedRatio"}, "6": {"property": "CriticalChanceBase"},
                         "8": {"property": "CriticalDamageBase"}, "9": {"property": "SpeedDelta"}}}}
# real shape captured from Enka (tid 61241 = 5-star, group 5)
RELIC = {"tid": 61241, "level": 15, "type": 1,
         "subAffixList": [{"affixId": 4, "cnt": 1, "step": 1}, {"affixId": 6, "cnt": 2, "step": 2},
                          {"affixId": 8, "cnt": 3, "step": 5}, {"affixId": 9, "cnt": 3, "step": 2}]}


def test_affix_lookup_and_subs():
    assert affix_property(SUB, 61241, 6) == "CriticalChanceBase"
    assert affix_property(SUB, 61241, 999) is None
    assert affix_property(SUB, "bad", 6) is None
    assert relic_subs(RELIC, SUB) == [("HPAddedRatio", 1), ("CriticalChanceBase", 2),
                                      ("CriticalDamageBase", 3), ("SpeedDelta", 3)]
    assert relic_subs({}, SUB) == []


def test_score():
    w = {"CriticalChanceBase": 1.0, "CriticalDamageBase": 1.0}
    s = score_relic(relic_subs(RELIC, SUB), w)
    assert s.total == 9 and s.wasted == 4 and s.efficiency == pytest.approx(5 / 9)
    assert score_relic([], w).efficiency == 0.0
    assert weights_for("nope") and weights_for("Shaman")["SpeedDelta"] == 1.0


def test_parse_profile_public_and_private():
    p = parse_profile({"detailInfo": {"uid": 8, "nickname": "A", "level": 70, "worldLevel": 6,
                                      "recordInfo": {"achievementCount": 10, "avatarCount": 3},
                                      "avatarDetailList": [{"avatarId": 1001}]}, "ttl": 10})
    assert (p.achievements, p.characters, len(p.avatars), p.ttl) == (10, 3, 1, 60)  # ttl floor 60s
    private = parse_profile({"detailInfo": {"uid": 8, "nickname": "B", "level": 1}})
    assert private.achievements is None and private.avatars == []
    for bad in [{}, None, {"detailInfo": "x"}]:
        with pytest.raises(EnkaError):
            parse_profile(bad)


def test_rank_rows():
    rows = [{"user_id": 1, "achievements": 5}, {"user_id": 2, "achievements": None},
            {"user_id": 3, "achievements": 9}]
    assert [r["user_id"] for r in rank_rows(rows, "achievements")] == [3, 1]
