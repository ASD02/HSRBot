import pytest
from cryptography.fernet import Fernet, InvalidToken
from genshin import errors as ge

from hsrbot.cogs.hoyolab import friendly_error, make_client, should_alert
from hsrbot.crypto import Vault
from hsrbot.db import Database

KEY = Fernet.generate_key().decode()


def test_vault_roundtrip_and_wrong_key():
    blob = Vault(KEY).encrypt("v2_secret")
    assert b"v2_secret" not in blob
    assert Vault(KEY).decrypt(blob) == "v2_secret"
    with pytest.raises(InvalidToken):
        Vault(Fernet.generate_key().decode()).decrypt(blob)


@pytest.mark.parametrize("bad", [None, "", "not-a-key"])
def test_vault_bad_key(bad):
    with pytest.raises(RuntimeError, match="FERNET_KEY"):
        Vault(bad)


def test_should_alert():
    assert should_alert(180, 240, False) is False  # 75%
    assert should_alert(216, 240, False) is True   # exactly 90%
    assert should_alert(240, 240, True) is False   # already alerted this fill
    assert should_alert(0, 0, False) is False      # bad data


def test_friendly_error():
    assert "invalid" in friendly_error(ge.InvalidCookies()).lower()
    assert "private" in friendly_error(ge.DataNotPublic()).lower()
    assert "already" in friendly_error(ge.AlreadyClaimed()).lower()
    assert "cooldown" in friendly_error(ge.RedemptionCooldown()).lower()
    assert "expired" in friendly_error(ge.RedemptionInvalid()).lower()
    assert "captcha" in friendly_error(ge.GeetestError({})).lower()
    assert "error" in friendly_error(ge.GenshinException()).lower()
    assert "wrong" in friendly_error(ValueError("boom")).lower()
    assert "boom" not in friendly_error(ValueError("boom"))  # raw errors may carry cookies


def test_make_client_cookie_names():
    assert "ltoken_v2" in make_client("1", "v2_abc", None).cookie_manager.cookies
    assert "ltoken" in make_client("1", "legacy", "800000001").cookie_manager.cookies


async def test_link_unlink_roundtrip_encrypted(tmp_path):
    db, v = Database(tmp_path / "t.db"), Vault(KEY)
    await db.connect()
    await db.execute("INSERT INTO hoyolab (user_id, ltuid, ltoken_enc, uid) VALUES (?,?,?,?)",
                     (1, "42", v.encrypt("v2_tok"), "800000001"))
    row = await db.fetchone("SELECT * FROM hoyolab WHERE user_id=1")
    assert b"v2_tok" not in bytes(row["ltoken_enc"]) and v.decrypt(row["ltoken_enc"]) == "v2_tok"
    assert await db.execute("DELETE FROM hoyolab WHERE user_id=1") == 1
    assert await db.fetchone("SELECT * FROM hoyolab WHERE user_id=1") is None
    await db.close()
