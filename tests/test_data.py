from hsrbot.data import GameData

CH = {
    "1": {"name": "Seele", "rarity": 5, "path": "Hunt", "element": "Quantum"},
    "2": {"name": "Asta", "rarity": 4, "path": "Harmony", "element": "Fire"},
    "3": {"name": "Blade", "rarity": 5, "path": "Destruction", "element": "Wind"},
    "4": {"name": "Sparkle Seele", "rarity": 5, "path": "Harmony", "element": "Quantum"},
}


def test_search_ranking_and_limits():
    gd = GameData.from_dicts(CH, {})
    names = [c["name"] for c in gd.search("character", "se")]
    assert names == ["Seele", "Sparkle Seele"]  # prefix first, then substring
    assert [c["name"] for c in gd.search("character", "BLA")] == ["Blade"]
    assert len(gd.search("character", "", limit=2)) == 2
    assert gd.search("character", "x" * 5000) == []


def test_get_exact():
    gd = GameData.from_dicts(CH, {})
    assert gd.get("character", "asta")["element"] == "Fire"
    assert gd.get("character", "nobody") is None


async def test_load_offline_without_cache(tmp_path):
    class Offline:
        def get(self, *a, **k):
            raise OSError("no network")

    gd = GameData(tmp_path)
    await gd.load(Offline())
    assert gd.characters == {}
