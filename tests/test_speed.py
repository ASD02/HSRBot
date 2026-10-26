import pytest

from hsrbot.speed import actions_in, av, cycle_budget, min_speed, parse_units, turn_order


def test_basics():
    assert av(100) == 100
    assert cycle_budget(1) == 150 and cycle_budget(3) == 350
    assert actions_in(134, 2) == 3
    assert actions_in(150, 1) == 2
    assert min_speed(2, 1) == pytest.approx(133.333, rel=1e-4)
    assert actions_in(min_speed(2, 1), 1) == 2  # breakpoint is exact


@pytest.mark.parametrize("bad", [0, -5])
def test_bad_speed(bad):
    with pytest.raises(ValueError):
        av(bad)


def test_bad_cycles_and_actions():
    with pytest.raises(ValueError):
        cycle_budget(0)
    with pytest.raises(ValueError):
        min_speed(0, 1)


def test_turn_order_and_ties():
    order = turn_order([("A", 100), ("B", 200)], 4)
    assert [n for n, _ in order] == ["B", "A", "B", "B"]
    assert [n for n, _ in turn_order([("X", 100), ("Y", 100)], 2)] == ["X", "Y"]


def test_parse_units():
    assert parse_units("Seele:134, Dr. Ratio: 103.5") == [("Seele", 134.0), ("Dr. Ratio", 103.5)]
    for bad in ["", "Seele", "Seele:abc", ":100", "A:0"]:
        with pytest.raises(ValueError):
            parse_units(bad)
