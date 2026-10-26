"""Patch / banner-phase / endgame-reset schedule. Dates come from data/schedule.json (hand-maintained)."""
import json
from dataclasses import dataclass
from datetime import date, datetime, time, timedelta, timezone
from pathlib import Path

REGIONS = {"Asia": 8, "Europe": 1, "America": -5}  # server UTC offsets
RESET_HOUR, PATCH_HOUR = 4, 11  # server-local
PHASE_DAYS = 21


@dataclass(frozen=True)
class Mode:
    name: str
    anchor: date
    period_days: int


@dataclass(frozen=True)
class Patch:
    version: str
    start: date


@dataclass(frozen=True)
class Schedule:
    estimated: bool
    patch_days: int
    patches: list
    modes: list


def load_schedule(path) -> Schedule:
    raw = json.loads(Path(path).read_text(encoding="utf-8"))
    return Schedule(
        estimated=raw.get("estimated", True),
        patch_days=raw.get("patch_days", 42),
        patches=sorted((Patch(p["version"], date.fromisoformat(p["start"])) for p in raw["patches"]),
                       key=lambda p: p.start),
        modes=[Mode(m["name"], date.fromisoformat(m["anchor"]), m["period_days"]) for m in raw["modes"]],
    )


def _at(d: date, hour: int, tz_hours: int) -> datetime:
    return datetime.combine(d, time(hour), timezone(timedelta(hours=tz_hours)))


def next_reset(mode: Mode, now: datetime, tz_hours: int) -> datetime:
    """First reset strictly after `now`."""
    start = _at(mode.anchor, RESET_HOUR, tz_hours)
    if now < start:
        return start
    period = timedelta(days=mode.period_days)
    return start + ((now - start) // period + 1) * period


def phases(schedule: Schedule, tz_hours: int) -> list:
    """[(version, phase_no, starts, ends)] across all listed patches, in order."""
    out = []
    for i, p in enumerate(schedule.patches):
        s = _at(p.start, PATCH_HOUR, tz_hours)
        end = (_at(schedule.patches[i + 1].start, PATCH_HOUR, tz_hours)
               if i + 1 < len(schedule.patches) else s + timedelta(days=schedule.patch_days))
        mid = min(s + timedelta(days=PHASE_DAYS), end)
        out += [(p.version, 1, s, mid), (p.version, 2, mid, end)]
    return out


def current_and_next(schedule: Schedule, now: datetime, tz_hours: int):
    """(current phase or None, next phase or None)."""
    cur = nxt = None
    for ph in phases(schedule, tz_hours):
        if ph[2] <= now < ph[3]:
            cur = ph
        elif ph[2] > now and nxt is None:
            nxt = ph
    return cur, nxt


def due_reminders(schedule: Schedule, now: datetime, tz_hours: int,
                  window: timedelta = timedelta(hours=24)) -> list[tuple[str, datetime]]:
    """Events starting within `window`, keyed for dedupe by (label, when)."""
    out = [(f"{m.name} resets", r) for m in schedule.modes
           if (r := next_reset(m, now, tz_hours)) - now <= window]
    out += [(f"Version {v} phase {n} starts", s) for v, n, s, _ in phases(schedule, tz_hours)
            if now < s <= now + window]
    return sorted(out, key=lambda e: e[1])
