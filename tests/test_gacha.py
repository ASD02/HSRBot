import random

import pytest

from hsrbot.gacha import BANNERS, expected_pulls, odds_by_budget, rate, simulate_pull

C, L = BANNERS["character"], BANNERS["lightcone"]


def test_rates():
    assert rate(C, 0) == 0.006
    assert rate(C, 73) == pytest.approx(0.066)
    assert rate(C, 89) == 1.0
    assert rate(L, 79) == 1.0
    assert rate(L, 62) == 0.008 and rate(L, 63) == pytest.approx(0.078)


def test_odds_bounds_and_monotonic():
    assert odds_by_budget(C, 0) == 0.0
    assert odds_by_budget(C, 180) == pytest.approx(1.0)
    assert odds_by_budget(C, 90, pity=0, guaranteed=True) == pytest.approx(1.0)
    assert odds_by_budget(C, 89, pity=0, guaranteed=True) < 1.0
    vals = [odds_by_budget(C, n) for n in (10, 50, 90, 120)]
    assert vals == sorted(vals)


def test_two_copies_needs_more():
    assert odds_by_budget(C, 90, copies=2) < odds_by_budget(C, 90, copies=1)
    # worst case: guaranteed win (90) + lost 50/50 (90) + guarantee (90)
    assert odds_by_budget(C, 270, copies=2, guaranteed=True) == pytest.approx(1.0)


def test_expected_pulls_reasonable():
    e = expected_pulls(C)
    assert 60 < e < 110
    assert expected_pulls(C, guaranteed=True) < e


@pytest.mark.parametrize("bad", [-1, 90, 1.5])
def test_bad_pity(bad):
    with pytest.raises(ValueError):
        odds_by_budget(C, 10, pity=bad)


def test_bad_pulls_and_copies():
    with pytest.raises(ValueError):
        odds_by_budget(C, -1)
    with pytest.raises(ValueError):
        odds_by_budget(C, 10, copies=0)


def test_simulate_hard_pity_and_guarantee():
    rng = random.Random(1)
    five, feat, pity, g = simulate_pull(C, 89, True, rng)
    assert five and feat and pity == 0 and g is False
    five, feat, pity, g = simulate_pull(C, 89, False, random.Random(2))
    assert five and pity == 0 and g == (not feat)
