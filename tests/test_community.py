import random
from datetime import date, datetime, timezone

import pytest

from hsrbot.cogs.community import story_cooldown_until
from hsrbot.feeds import parse_codes, parse_rss
from hsrbot.i18n import tr
from hsrbot.schedule import Patch, Schedule
from hsrbot.trivia import make_question
from hsrbot.uid import validate_uid

UTC = timezone.utc


def test_uid():
    assert validate_uid(" 700123456 ") == ("700123456", "Europe")
    assert validate_uid("800123456")[1] == "Asia"
    for bad in ["", "12345678", "12345678901", "abcdefghi", "700 123 456"]:
        with pytest.raises(ValueError):
            validate_uid(bad)


def test_i18n_fallback():
    assert "UID 7" in tr("ja", "linked", uid=7)
    assert tr("xx-YY", "no_results") == "Nothing found."
    assert tr(None, "no_results") == "Nothing found."
    assert tr("zh-TW", "no_results")  # unknown region variant still returns text


def test_parse_codes():
    assert parse_codes(["abcd1234", {"code": "STARRAIL", "rewards": "50 Jade"}, "bad!", 5, {"x": 1}]) == [
        ("ABCD1234", ""), ("STARRAIL", "50 Jade")]
    assert parse_codes({"not": "a list"}) == []


RSS = """<rss><channel>
<item><title>Patch 4.7</title><link>https://example.com/a</link><guid>g1</guid></item>
<item><title>Bad link</title><link>javascript:alert(1)</link></item>
<item><title>Older</title><link>https://example.com/b</link></item>
</channel></rss>"""


def test_parse_rss():
    items = parse_rss(RSS)
    assert [(x["id"], x["title"]) for x in items] == [("g1", "Patch 4.7"), ("https://example.com/b", "Older")]
    assert parse_rss("<not xml") == []


def test_story_cooldown():
    s = Schedule(True, 42, [Patch("4.7", date(2026, 11, 11))], [])
    assert story_cooldown_until(s, datetime(2026, 11, 15, tzinfo=UTC)) is not None
    assert story_cooldown_until(s, datetime(2026, 12, 15, tzinfo=UTC)) is None
    assert story_cooldown_until(s, datetime(2026, 11, 1, tzinfo=UTC)) is None


CH = {str(n): {"name": f"C{n}", "rarity": 5, "path": p, "element": e}
      for n, (p, e) in enumerate([("Hunt", "Ice"), ("Hunt", "Fire"), ("Erudition", "Wind"),
                                  ("Harmony", "Ice"), ("Nihility", "Quantum"), ("Abundance", "Imaginary")])}


def test_trivia():
    for kind in ("element", "path", "guess"):
        q = make_question(CH, random.Random(3), kind)
        assert q.answer in q.options and len(set(q.options)) == len(q.options)
    assert make_question({}, random.Random(1)) is None
    assert make_question(dict(list(CH.items())[:3]), random.Random(1)) is None
