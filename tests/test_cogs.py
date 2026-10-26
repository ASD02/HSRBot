import importlib
import pkgutil

import pytest

from hsrbot import cogs


def test_every_cog_imports_and_has_setup():
    for m in pkgutil.iter_modules(cogs.__path__):
        mod = importlib.import_module(f"hsrbot.cogs.{m.name}")
        assert hasattr(mod, "setup"), m.name


def test_format_plan():
    from hsrbot.cogs.warp import format_plan
    out = format_plan("character", 90, 0, True, 1)
    assert "100.0%" in out and "Stellar Jade" in out


def test_lookup_embed():
    from hsrbot.cogs.lookup import info_embed
    e = info_embed({"name": "Seele", "rarity": 5, "path": "Hunt", "element": "Quantum"}, "character")
    assert e.title == "Seele" and e.fields[0].value == "★★★★★"
    info_embed({}, "lightcone")  # missing keys must not raise
