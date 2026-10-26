import logging
from datetime import datetime, timedelta, timezone

import discord
import genshin
from discord import app_commands
from discord.ext import commands, tasks
from genshin import errors as ge

from ..crypto import Vault

log = logging.getLogger("hsrbot.hoyolab")
ALERT_FRACTION = 0.9
TOS_WARNING = ("⚠️ Automating the daily check-in may violate HoYoverse's Terms of Service and could put "
               "your account at risk. Only enable it if you accept that risk.")

_MESSAGES = [  # first isinstance match wins, so subclasses come before parents
    ((ge.InvalidCookies,), "Your HoYoLAB cookies are invalid or expired. Run /hoyolab link again."),
    ((ge.TooManyRequests, ge.VisitsTooFrequently), "HoYoLAB is rate limiting requests. Try again in a minute."),
    ((ge.DataNotPublic, ge.UserNotesAccessDenied),
     "Real-time notes are private. Enable them in the HoYoLAB app (Battle Chronicle > Settings)."),
    ((ge.AlreadyClaimed,), "Today's check-in reward was already claimed."),
    ((ge.RedemptionCooldown,), "Redeem cooldown: wait a few seconds and try again."),
    ((ge.RedemptionClaimed,), "That code was already redeemed on this account."),
    ((ge.RedemptionInvalid,), "That code is invalid or has expired."),
    ((ge.RedeemGameLevelTooLow,), "Your Trailblaze Level is too low to redeem codes."),
    ((ge.DailyGeetestTriggered, ge.GeetestError), "HoYoLAB asked for a captcha, so I can't do this automatically."),
    ((ge.AccountNotFound,), "No Star Rail account found on that HoYoLAB login."),
    ((ge.GenshinException,), "HoYoLAB returned an error. Try again later."),
]


def friendly_error(exc: Exception) -> str:
    for types, msg in _MESSAGES:
        if isinstance(exc, types):
            return msg
    return "Something went wrong talking to HoYoLAB."


def should_alert(current: int, maximum: int, already_alerted: bool) -> bool:
    return maximum > 0 and current >= ALERT_FRACTION * maximum and not already_alerted


def make_client(ltuid: str, token: str, uid: str | None) -> genshin.Client:
    suffix = "_v2" if token.startswith("v2_") else ""
    return genshin.Client({f"ltuid{suffix}": ltuid, f"ltoken{suffix}": token},
                          game=genshin.Game.STARRAIL, uid=int(uid) if uid else None)


def ts(delta: timedelta, style: str = "R") -> str:
    return f"<t:{int((datetime.now(timezone.utc) + delta).timestamp())}:{style}>"


class LinkModal(discord.ui.Modal, title="Link HoYoLAB"):
    ltuid = discord.ui.TextInput(label="ltuid_v2 (or ltuid)", max_length=20)
    ltoken = discord.ui.TextInput(label="ltoken_v2 (or ltoken)", max_length=2000)
    uid = discord.ui.TextInput(label="Star Rail UID (optional)", required=False, max_length=10)

    def __init__(self, cog):
        super().__init__()
        self.cog = cog

    async def on_submit(self, i: discord.Interaction):
        await i.response.defer(ephemeral=True)
        ltuid, token, uid = self.ltuid.value.strip(), self.ltoken.value.strip(), self.uid.value.strip() or None
        if not ltuid.isdigit() or (uid and not uid.isdigit()):
            return await i.followup.send("ltuid and UID must be numbers.", ephemeral=True)
        try:
            client = make_client(ltuid, token, uid)
            if not uid:
                acc = next((a for a in await client.get_game_accounts() if a.game_biz.startswith("hkrpg")), None)
                if not acc:
                    return await i.followup.send(friendly_error(ge.AccountNotFound()), ephemeral=True)
                uid = str(acc.uid)
                client = make_client(ltuid, token, uid)
            await client.get_starrail_notes()  # real call: proves the cookies work
        except Exception as e:
            return await i.followup.send(friendly_error(e), ephemeral=True)  # never echo/log cookies
        await self.cog.bot.db.execute(
            "INSERT INTO hoyolab (user_id, ltuid, ltoken_enc, uid) VALUES (?,?,?,?) "
            "ON CONFLICT(user_id) DO UPDATE SET ltuid=excluded.ltuid, ltoken_enc=excluded.ltoken_enc, uid=excluded.uid",
            (i.user.id, ltuid, self.cog.vault.encrypt(token), uid))
        await i.followup.send(f"Linked UID {uid}. Your token is stored encrypted; /hoyolab unlink removes it.",
                              ephemeral=True)


class ConfirmCheckin(discord.ui.View):
    def __init__(self, cog, user_id: int):
        super().__init__(timeout=60)
        self.cog, self.user_id = cog, user_id

    @discord.ui.button(label="I accept the risk, enable", style=discord.ButtonStyle.danger)
    async def confirm(self, i: discord.Interaction, _):
        if i.user.id != self.user_id:
            return await i.response.send_message("Not your button.", ephemeral=True)
        await self.cog.bot.db.execute("UPDATE hoyolab SET checkin=1 WHERE user_id=?", (self.user_id,))
        self.stop()
        await i.response.edit_message(content="Daily check-in enabled.", view=None)


class HoyolabGroup(app_commands.Group):
    def __init__(self, cog):
        super().__init__(name="hoyolab", description="HoYoLAB account features")
        self.cog = cog

    async def _client(self, i: discord.Interaction):
        row = await self.cog.bot.db.fetchone("SELECT * FROM hoyolab WHERE user_id=?", (i.user.id,))
        if not row:
            await i.response.send_message("Link first with /hoyolab link.", ephemeral=True)
            return None
        return self.cog.client_for(row)

    @app_commands.command(description="Link your HoYoLAB cookies (stored encrypted)")
    async def link(self, i: discord.Interaction):
        await i.response.send_modal(LinkModal(self.cog))

    @app_commands.command(description="Real-time notes: stamina, dailies, expeditions")
    async def notes(self, i: discord.Interaction):
        client = await self._client(i)
        if not client:
            return
        await i.response.defer(ephemeral=True)
        try:
            n = await client.get_starrail_notes()
        except Exception as e:
            return await i.followup.send(friendly_error(e), ephemeral=True)
        e = discord.Embed(title="Real-time notes")
        full = ("full" if n.current_stamina >= n.max_stamina else ts(n.stamina_recover_time))
        e.add_field(name="Trailblaze Power", value=f"{n.current_stamina}/{n.max_stamina} (full {full})")
        e.add_field(name="Daily Training", value=f"{n.current_train_score}/{n.max_train_score}")
        e.add_field(name="Echo of War", value=f"{n.remaining_weekly_discounts}/{n.max_weekly_discounts} left")
        exp = [f"{x.name}: " + ("done" if x.status == "Finished" else ts(x.remaining_time)) for x in n.expeditions]
        e.add_field(name="Assignments", value="\n".join(exp) or "none", inline=False)
        await i.followup.send(embed=e, ephemeral=True)

    @app_commands.command(description="DM me when Trailblaze Power is nearly full")
    async def stamina_alert(self, i: discord.Interaction, enabled: bool):
        if not await self._set(i, "stamina_alert", int(enabled)):
            return
        await i.response.send_message(f"Stamina alerts {'on' if enabled else 'off'}.", ephemeral=True)

    @app_commands.command(description="Auto daily check-in (ToS risk, asks for confirmation)")
    async def checkin(self, i: discord.Interaction, enabled: bool):
        if enabled:
            if not await self.cog.bot.db.fetchone("SELECT 1 FROM hoyolab WHERE user_id=?", (i.user.id,)):
                return await i.response.send_message("Link first with /hoyolab link.", ephemeral=True)
            return await i.response.send_message(TOS_WARNING, view=ConfirmCheckin(self.cog, i.user.id),
                                                 ephemeral=True)
        if await self._set(i, "checkin", 0):
            await i.response.send_message("Daily check-in disabled.", ephemeral=True)

    async def _set(self, i, col: str, value: int) -> bool:
        n = await self.cog.bot.db.execute(f"UPDATE hoyolab SET {col}=?, last_alert=NULL WHERE user_id=?",
                                          (value, i.user.id))  # col is a literal from this file only
        if not n:
            await i.response.send_message("Link first with /hoyolab link.", ephemeral=True)
        return bool(n)

    @app_commands.command(description="Redeem a code on your linked account")
    async def redeem(self, i: discord.Interaction, code: app_commands.Range[str, 4, 32]):
        client = await self._client(i)
        if not client:
            return
        await i.response.defer(ephemeral=True)
        try:
            await client.redeem_code(code.strip(), game=genshin.Game.STARRAIL)
        except Exception as e:
            return await i.followup.send(friendly_error(e), ephemeral=True)
        await i.followup.send("Code redeemed! Check your in-game mail.", ephemeral=True)

    @app_commands.command(description="Delete your stored HoYoLAB login")
    async def unlink(self, i: discord.Interaction):
        n = await self.cog.bot.db.execute("DELETE FROM hoyolab WHERE user_id=?", (i.user.id,))
        await i.response.send_message("Unlinked and deleted." if n else "Nothing was linked.", ephemeral=True)


class Hoyolab(commands.Cog):
    def __init__(self, bot, vault: Vault):
        self.bot, self.vault = bot, vault
        bot.tree.add_command(HoyolabGroup(self))
        self.stamina_loop.start()
        self.checkin_loop.start()

    def cog_unload(self):
        self.stamina_loop.cancel()
        self.checkin_loop.cancel()
        self.bot.tree.remove_command("hoyolab")

    def client_for(self, row) -> genshin.Client:
        return make_client(row["ltuid"], self.vault.decrypt(row["ltoken_enc"]), row["uid"])

    @tasks.loop(minutes=10)
    async def stamina_loop(self):
        for row in await self.bot.db.fetchall("SELECT * FROM hoyolab WHERE stamina_alert=1"):
            try:
                n = await self.client_for(row).get_starrail_notes()
                alerted = row["last_alert"] is not None
                if should_alert(n.current_stamina, n.max_stamina, alerted):
                    user = await self.bot.fetch_user(row["user_id"])
                    await user.send(f"Trailblaze Power is {n.current_stamina}/{n.max_stamina}. "
                                    f"Full {ts(n.stamina_recover_time)}.")
                    await self.bot.db.execute("UPDATE hoyolab SET last_alert='1' WHERE user_id=?", (row["user_id"],))
                elif alerted and n.current_stamina < ALERT_FRACTION * n.max_stamina:
                    await self.bot.db.execute("UPDATE hoyolab SET last_alert=NULL WHERE user_id=?", (row["user_id"],))
            except discord.Forbidden:  # DMs closed: mark alerted so we don't retry every 10 minutes
                await self.bot.db.execute("UPDATE hoyolab SET last_alert='1' WHERE user_id=?", (row["user_id"],))
            except Exception as e:
                log.warning("stamina check failed for %s: %s", row["user_id"], type(e).__name__)

    @tasks.loop(hours=1)
    async def checkin_loop(self):
        day = datetime.now(timezone.utc).date().isoformat()
        for row in await self.bot.db.fetchall("SELECT * FROM hoyolab WHERE checkin=1"):
            marker = f"checkin:{row['user_id']}:{day}"
            if await self.bot.db.fetchone("SELECT 1 FROM sent_markers WHERE marker=?", (marker,)):
                continue
            try:
                await self.client_for(row).claim_daily_reward(game=genshin.Game.STARRAIL, reward=False)
            except ge.AlreadyClaimed:
                pass
            except Exception as e:
                log.warning("check-in failed for %s: %s", row["user_id"], type(e).__name__)
                continue  # no marker, so the next hourly run retries
            await self.bot.db.mark_sent(marker)

    @stamina_loop.before_loop
    @checkin_loop.before_loop
    async def _wait(self):
        await self.bot.wait_until_ready()


async def setup(bot):
    try:
        vault = Vault(bot.config.fernet_key)
    except RuntimeError as e:
        log.warning("%s", e)
        return
    await bot.add_cog(Hoyolab(bot, vault))
