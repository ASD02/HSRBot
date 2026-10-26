"""Relic roll-efficiency scoring.

efficiency = (sum of weight*rolls over substats) / total rolls, 0..1. `cnt` from Enka already
includes the initial roll. Weights are rough per-Path heuristics, not per-character builds.
"""
from dataclasses import dataclass

_CRIT = {"CriticalChanceBase": 1.0, "CriticalDamageBase": 1.0}
_TANK = {"HPAddedRatio": 0.6, "DefenceAddedRatio": 0.6, "SpeedDelta": 0.8}
WEIGHTS = {
    "Warrior": {**_CRIT, "AttackAddedRatio": 0.8, "SpeedDelta": 0.6, "BreakDamageAddedRatioBase": 0.3},
    "Rogue": {**_CRIT, "AttackAddedRatio": 0.8, "SpeedDelta": 0.7, "BreakDamageAddedRatioBase": 0.3},
    "Mage": {**_CRIT, "AttackAddedRatio": 0.8, "SpeedDelta": 0.6},
    "Warlock": {**_CRIT, "AttackAddedRatio": 0.8, "SpeedDelta": 0.8, "StatusProbabilityBase": 0.6,
                "BreakDamageAddedRatioBase": 0.3},
    "Shaman": {"SpeedDelta": 1.0, "BreakDamageAddedRatioBase": 0.8, "CriticalDamageBase": 0.6,
               "HPAddedRatio": 0.4, "DefenceAddedRatio": 0.3, "StatusResistanceBase": 0.2},
    "Knight": {**_TANK, "BreakDamageAddedRatioBase": 0.5, "StatusResistanceBase": 0.3},
    "Priest": {**_TANK, "StatusResistanceBase": 0.3},
    "Memory": {**_CRIT, "SpeedDelta": 0.7, "HPAddedRatio": 0.6, "AttackAddedRatio": 0.4},
}
DEFAULT_WEIGHTS = {**_CRIT, "AttackAddedRatio": 0.6, "SpeedDelta": 0.7, "HPAddedRatio": 0.3}
SLOT_NAMES = {1: "Head", 2: "Hands", 3: "Body", 4: "Feet", 5: "Sphere", 6: "Rope"}


@dataclass(frozen=True)
class RelicScore:
    efficiency: float
    wasted: int  # rolls spent on zero-weight substats
    total: int


def affix_property(sub_table: dict, tid, affix_id) -> str | None:
    """Relic ids start with 3/4/5/6 for 2/3/4/5-star; the sub-affix group is that rarity."""
    group = str(int(str(tid)[0]) - 1) if str(tid)[:1].isdigit() else None
    entry = sub_table.get(group, {}).get("affixes", {}).get(str(affix_id))
    return entry.get("property") if entry else None


def relic_subs(relic: dict, sub_table: dict) -> list[tuple[str, int]]:
    out = []
    for s in relic.get("subAffixList") or []:
        prop = affix_property(sub_table, relic.get("tid"), s.get("affixId"))
        if prop and isinstance(s.get("cnt"), int) and s["cnt"] > 0:
            out.append((prop, s["cnt"]))
    return out


def score_relic(subs: list[tuple[str, int]], weights: dict) -> RelicScore:
    total = sum(c for _, c in subs)
    if total == 0:
        return RelicScore(0.0, 0, 0)
    useful = sum(weights.get(p, 0.0) * c for p, c in subs)
    wasted = sum(c for p, c in subs if weights.get(p, 0.0) == 0)
    return RelicScore(useful / total, wasted, total)


def weights_for(path: str | None) -> dict:
    return WEIGHTS.get(path, DEFAULT_WEIGHTS)
