"""Speed / Action Value math. Cycle 1 = 150 AV, every later cycle = 100 AV."""
import math

FIRST_CYCLE_AV = 150
CYCLE_AV = 100
EPS = 1e-9


def _spd(spd: float) -> float:
    if not spd or spd <= 0:
        raise ValueError("SPD must be greater than 0")
    return float(spd)


def av(spd: float) -> float:
    return 10000 / _spd(spd)


def cycle_budget(cycles: int) -> int:
    if cycles < 1:
        raise ValueError("cycles must be at least 1")
    return FIRST_CYCLE_AV + CYCLE_AV * (cycles - 1)


def actions_in(spd: float, cycles: int) -> int:
    return math.floor(cycle_budget(cycles) * _spd(spd) / 10000 + EPS)


def min_speed(actions: int, cycles: int) -> float:
    if actions < 1:
        raise ValueError("actions must be at least 1")
    return actions * 10000 / cycle_budget(cycles)


def parse_units(text: str) -> list[tuple[str, float]]:
    """'Seele:134, Bronya:99' -> [('Seele', 134.0), ('Bronya', 99.0)]"""
    units = []
    for part in text.split(","):
        name, sep, spd = part.rpartition(":")
        if not sep or not name.strip():
            raise ValueError(f"expected Name:SPD, got {part.strip()!r}")
        try:
            units.append((name.strip(), float(spd)))
        except ValueError:
            raise ValueError(f"SPD must be a number in {part.strip()!r}") from None
        _spd(units[-1][1])
    if not units:
        raise ValueError("no units given")
    return units


def turn_order(units: list[tuple[str, float]], n: int) -> list[tuple[str, float]]:
    """First n actions as (name, AV elapsed); ties go to the earlier-listed unit."""
    if n < 1:
        raise ValueError("n must be at least 1")
    nxt = [av(s) for _, s in units]
    out = []
    for _ in range(n):
        i = min(range(len(units)), key=lambda k: (nxt[k], k))
        out.append((units[i][0], nxt[i]))
        nxt[i] += av(units[i][1])
    return out
