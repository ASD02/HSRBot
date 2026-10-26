import pytest

from hsrbot.gacha import BANNERS, pity_cdf


def test_pity_cdf():
    c = BANNERS["character"]
    assert pity_cdf(c, 1) == pytest.approx(0.006) and pity_cdf(c, 90) == 1.0 == pity_cdf(c, 500)
    with pytest.raises(ValueError):
        pity_cdf(c, 0)
