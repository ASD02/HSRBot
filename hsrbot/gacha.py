"""Warp (gacha) math. Pure functions; pity = pulls since the last 5-star."""
import random
from dataclasses import dataclass

MAX_PULLS = 2000


@dataclass(frozen=True)
class Banner:
    name: str
    base: float
    soft_start: int  # first pull number with a boosted rate
    step: float
    hard: int
    featured_rate: float


BANNERS = {
    "character": Banner("Character", 0.006, 74, 0.06, 90, 0.5),
    "lightcone": Banner("Light Cone", 0.008, 64, 0.07, 80, 0.75),
}


def _check(banner: Banner, pity: int) -> None:
    if not isinstance(pity, int) or not 0 <= pity < banner.hard:
        raise ValueError(f"pity must be an integer from 0 to {banner.hard - 1}")


def rate(banner: Banner, pity: int) -> float:
    """Chance that the next pull is a 5-star."""
    _check(banner, pity)
    n = pity + 1
    if n >= banner.hard:
        return 1.0
    if n >= banner.soft_start:
        return min(1.0, banner.base + banner.step * (n - banner.soft_start + 1))
    return banner.base


def _success_curve(banner: Banner, pity: int, guaranteed: bool, copies: int):
    """Yield P(at least `copies` featured 5-stars) after each successive pull."""
    _check(banner, pity)
    if copies < 1:
        raise ValueError("copies must be at least 1")
    dist = {(pity, bool(guaranteed), 0): 1.0}
    done = 0.0
    while True:
        nxt: dict = {}
        for (p, g, c), prob in dist.items():
            r = rate(banner, p)
            if r < 1.0:
                k = (p + 1, g, c)
                nxt[k] = nxt.get(k, 0.0) + prob * (1 - r)
            win = 1.0 if g else banner.featured_rate
            if win > 0:
                if c + 1 >= copies:
                    done += prob * r * win
                else:
                    k = (0, False, c + 1)
                    nxt[k] = nxt.get(k, 0.0) + prob * r * win
            if win < 1:
                k = (0, True, c)
                nxt[k] = nxt.get(k, 0.0) + prob * r * (1 - win)
        dist = nxt
        yield done


def odds_by_budget(banner: Banner, pulls: int, pity: int = 0,
                   guaranteed: bool = False, copies: int = 1) -> float:
    if not isinstance(pulls, int) or not 0 <= pulls <= MAX_PULLS:
        raise ValueError(f"pulls must be an integer from 0 to {MAX_PULLS}")
    if pulls == 0:
        _check(banner, pity)
        return 0.0
    curve = _success_curve(banner, pity, guaranteed, copies)
    for _ in range(pulls):
        done = next(curve)
    return min(1.0, done)


def expected_pulls(banner: Banner, pity: int = 0, guaranteed: bool = False, copies: int = 1) -> float:
    total, prev = 0.0, 0.0
    for t, done in enumerate(_success_curve(banner, pity, guaranteed, copies)):
        total += 1.0 - prev  # P(not finished before pull t+1)
        prev = done
        if 1.0 - done < 1e-12 or t > MAX_PULLS:
            return total
    return total


def simulate_pull(banner: Banner, pity: int, guaranteed: bool, rng: random.Random):
    """One pull. Returns (is_5star, is_featured, new_pity, new_guaranteed)."""
    if rng.random() >= rate(banner, pity):
        return False, False, pity + 1, guaranteed
    featured = guaranteed or rng.random() < banner.featured_rate
    return True, featured, 0, not featured


def pity_cdf(banner: Banner, n: int) -> float:
    """P(the first 5-star arrives within n pulls from pity 0); n past hard pity is clamped."""
    if not isinstance(n, int) or n < 1:
        raise ValueError("n must be an integer of at least 1")
    miss = 1.0
    for k in range(min(n, banner.hard)):
        miss *= 1 - rate(banner, k)
    return 1 - miss
