from datetime import date, datetime, timedelta, timezone

from hsrbot.schedule import Mode, Patch, Schedule, current_and_next, due_reminders, next_reset

UTC = timezone.utc
MODE = Mode("MoC", date(2026, 7, 15), 42)
SCHED = Schedule(True, 42, [Patch("4.7", date(2026, 11, 11)), Patch("4.8", date(2026, 12, 23))], [MODE])


def test_next_reset_boundaries():
    start = datetime(2026, 7, 14, 20, tzinfo=UTC)  # 04:00 UTC+8
    assert next_reset(MODE, start - timedelta(days=5), 8) == start
    assert next_reset(MODE, start, 8) == start + timedelta(days=42)  # just reset -> next one
    assert next_reset(MODE, start + timedelta(days=50), 8) == start + timedelta(days=84)


def test_regions_shift_instant():
    now = datetime(2026, 7, 1, tzinfo=UTC)
    assert next_reset(MODE, now, -5) - next_reset(MODE, now, 8) == timedelta(hours=13)


def test_current_and_next_phase():
    cur, nxt = current_and_next(SCHED, datetime(2026, 11, 20, tzinfo=UTC), 8)
    assert cur[:2] == ("4.7", 1) and nxt[:2] == ("4.7", 2)
    cur, nxt = current_and_next(SCHED, datetime(2026, 11, 1, tzinfo=UTC), 8)
    assert cur is None and nxt[:2] == ("4.7", 1)
    cur, nxt = current_and_next(SCHED, datetime(2027, 3, 1, tzinfo=UTC), 8)
    assert cur is None and nxt is None  # past the listed schedule


def test_due_reminders_window():
    reset = next_reset(MODE, datetime(2026, 8, 1, tzinfo=UTC), 8)
    assert due_reminders(SCHED, reset - timedelta(hours=23), 8)[0][0] == "MoC resets"
    assert due_reminders(SCHED, reset - timedelta(days=3), 8) == []
