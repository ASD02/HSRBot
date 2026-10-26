import json
import logging
import os
from datetime import datetime, timedelta, timezone

import discord
from discord import app_commands
from discord.ext import commands, tasks

from ..feeds import parse_codes, parse_rss
from ..i18n import tr
from ..schedule import REGIONS, load_schedule, phases
from ..uid import validate_uid

log = logging.getLogger("hsrbot.community")
STORY_SPOILER_DAYS = 14
CHANNEL_KINDS = ["codes", "news", "leaks", "announce"]


def story_cooldown_until(schedule, now: datetime, tz_hours: int = 8) -> datetime | None:
    """End of the story-spoiler cooldown if a patch started within the last STORY_SPOILER_DAYS days."""
    for _v, n, start, _end in phases(schedule, tz_hours):
        if n == 1 and start <= now < start + timedelta(days=STORY_SPOILER_DAYS):
            return start + timedelta(days=STORY_SPOILER_DAYS)
    return None


class Setup(app_commands.Group):
    def __init__(self, cog):
        super().__init__(name="setup", description="Configure the bot for this server",
                         guild_only=True, default_permissions=discord.Permissions(manage_guild=True))
        self.cog = cog

    @app_commands.command(description="Set the channel for codes, news, leaks, or announcements")
    @app_commands.choices(kind=[app_commands.Choice(name=k, value=k) for k in CHANNEL_KINDS])
    async def channel(self, i: discord.Interaction, kind: str, channel: discord.TextChannel):
        await self.cog.bot.db.set_conf(i.guild_id, f"{kind}_channel", str(channel.id))
        await i.response.send_message(f"{kind} channel set to {channel.mention}", ephemeral=True)

    @app_commands.command(description="Set the role pinged for reminders, or the opt-in leaks role")
    @app_commands.choices(kind=[app_commands.Choice(name="ping", value="ping_role"),
                                app_commands.Choice(name="leaks", value="leaks_role")])
    async def role(self, i: discord.Interaction, kind: str, role: discord.Role):
        await self.cog.bot.db.set_conf(i.guild_id, kind, str(role.id))
        await i.response.send_message(f"Saved {role.name}", ephemeral=True)

    @app_commands.command(description="Set the server region used for reset times")
    @app_commands.choices(region=[app_commands.Choice(name=r, value=r) for r in REGIONS])
    async def region(self, i: discord.Interaction, region: str):
        await self.cog.bot.db.set_conf(i.guild_id, "region", region)
        await i.response.send_message(f"Region set to {region}", ephemeral=True)


class UIDBoard(app_commands.Group):
    def __init__(self, cog):
        super().__init__(name="uid", description="Co-op / friend-finding board", guild_only=True)
        self.cog = cog

    @app_commands.command(description="Post your UID, e.g. note: need a Ruan Mei support")
    async def post(self, i: discord.Interaction, uid: str, note: app_commands.Range[str, 0, 100] = ""):
        try:
            uid, region = validate_uid(uid)
        except ValueError as e:
            return await i.response.send_message(str(e), ephemeral=True)
        await self.cog.bot.db.execute(
            "INSERT OR REPLACE INTO uid_board VALUES (?,?,?,?,?)", (i.guild_id, i.user.id, uid, region, note))
        await i.response.send_message(tr(i.locale, "uid_posted"), ephemeral=True)

    @app_commands.command(description="Browse the board")
    @app_commands.choices(region=[app_commands.Choice(name=r, value=r) for r in ["America", "Europe", "Asia", "CN"]])
    async def find(self, i: discord.Interaction, region: str | None = None):
        sql, args = "SELECT * FROM uid_board WHERE guild_id=?", [i.guild_id]
        if region:
            sql, args = sql + " AND region=?", args + [region]
        rows = await self.cog.bot.db.fetchall(sql + " LIMIT 20", tuple(args))
        if not rows:
            return await i.response.send_message(tr(i.locale, "no_results"), ephemeral=True)
        await i.response.send_message(
            "\n".join(f"<@{r['user_id']}> `{r['uid']}` ({r['region']}) {discord.utils.escape_markdown(r['note'])}"
                      for r in rows), allowed_mentions=discord.AllowedMentions.none())

    @app_commands.command(description="Remove your entry")
    async def remove(self, i: discord.Interaction):
        await self.cog.bot.db.execute("DELETE FROM uid_board WHERE guild_id=? AND user_id=?", (i.guild_id, i.user.id))
        await i.response.send_message(tr(i.locale, "uid_removed"), ephemeral=True)


class Community(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.schedule = load_schedule(bot.config.data_dir / "schedule.json")
        bot.tree.add_command(Setup(self))
        bot.tree.add_command(UIDBoard(self))
        self.feeds.start()

    def cog_unload(self):
        self.feeds.cancel()
        self.bot.tree.remove_command("setup")
        self.bot.tree.remove_command("uid")

    # ---- codes ----
    @app_commands.command(description="Add a redemption code and announce it (bot owner)")
    async def addcode(self, i: discord.Interaction, code: str, rewards: str = ""):
        if not await self.bot.is_owner(i.user):
            return await i.response.send_message("Owner only.", ephemeral=True)
        parsed = parse_codes([{"code": code, "rewards": rewards}])
        if not parsed:
            return await i.response.send_message("Codes are 8-16 letters/digits.", ephemeral=True)
        await self._store_code(*parsed[0])
        await i.response.send_message(f"Added {parsed[0][0]}", ephemeral=True)

    @app_commands.command(description="Show known redemption codes")
    async def codes(self, i: discord.Interaction):
        rows = await self.bot.db.fetchall("SELECT * FROM codes ORDER BY added_at DESC LIMIT 15")
        text = "\n".join(f"`{r['code']}` {r['rewards']}" for r in rows) or "No codes yet."
        await i.response.send_message(text + "\nRedeem at hsr.hoyoverse.com/gift")

    async def _store_code(self, code: str, rewards: str):
        await self.bot.db.execute("INSERT OR IGNORE INTO codes VALUES (?,?,?)",
                                  (code, rewards, datetime.now(timezone.utc).isoformat()))

    async def _fetch(self, url: str, as_json: bool):
        try:
            async with self.bot.session.get(url, timeout=20) as r:
                r.raise_for_status()
                return json.loads(await r.text()) if as_json else await r.text()
        except Exception as e:
            log.warning("feed %s failed: %s", url, e)
            return None

    @tasks.loop(minutes=15)
    async def feeds(self):
        if url := os.environ.get("CODES_URL"):
            for code, rewards in parse_codes(await self._fetch(url, True)):
                await self._store_code(code, rewards)
        news = parse_rss(text) if (url := os.environ.get("NEWS_RSS_URL")) and (text := await self._fetch(url, False)) else []
        for guild in self.bot.guilds:
            if ch := await self._chan(guild, "codes_channel"):
                for r in await self.bot.db.fetchall("SELECT * FROM codes"):
                    if await self.bot.db.mark_sent(f"code:{guild.id}:{r['code']}"):
                        await self._send(ch, f"New code: `{r['code']}` {r['rewards']}")
            if ch := await self._chan(guild, "news_channel"):
                for n in reversed(news):
                    if await self.bot.db.mark_sent(f"news:{guild.id}:{n['id']}"):
                        await self._send(ch, f"**{n['title']}**\n{n['link']}")

    @feeds.before_loop
    async def _wait(self):
        await self.bot.wait_until_ready()

    async def _chan(self, guild, key):
        cid = await self.bot.db.get_conf(guild.id, key)
        return guild.get_channel(int(cid)) if cid else None

    @staticmethod
    async def _send(ch, text):
        try:
            await ch.send(text, allowed_mentions=discord.AllowedMentions.none())
        except discord.HTTPException as e:
            log.warning("send failed: %s", e)

    # ---- leaks / spoilers ----
    @app_commands.command(description="Opt in or out of the leaks channel")
    @app_commands.guild_only()
    async def leaks(self, i: discord.Interaction):
        rid = await self.bot.db.get_conf(i.guild_id, "leaks_role")
        role = i.guild.get_role(int(rid)) if rid else None
        if not role:
            return await i.response.send_message("An admin hasn't set a leaks role (/setup role).", ephemeral=True)
        try:
            if role in i.user.roles:
                await i.user.remove_roles(role)
                msg = "You left the leaks channel."
            else:
                await i.user.add_roles(role)
                msg = "You joined the leaks channel."
        except discord.Forbidden:
            msg = "I can't manage that role. Move my role above it."
        await i.response.send_message(msg, ephemeral=True)

    @app_commands.command(description="Post text behind a spoiler tag. Story spoilers wait out the post-patch cooldown")
    @app_commands.choices(kind=[app_commands.Choice(name="leak", value="leak"),
                                app_commands.Choice(name="story", value="story")])
    @app_commands.guild_only()
    async def spoiler(self, i: discord.Interaction, kind: str, text: app_commands.Range[str, 1, 1500]):
        leaks_id = await self.bot.db.get_conf(i.guild_id, "leaks_channel")
        in_leaks = leaks_id is not None and str(i.channel_id) == leaks_id
        until = story_cooldown_until(self.schedule, datetime.now(timezone.utc))
        if (kind == "leak" or until) and not in_leaks:
            where = f"<#{leaks_id}>" if leaks_id else "a leaks channel (ask an admin to /setup one)"
            why = "Leaks" if kind == "leak" else f"Story spoilers are in cooldown until <t:{int(until.timestamp())}:D>, so they"
            return await i.response.send_message(f"{why} go in {where}.", ephemeral=True)
        safe = text.replace("||", "")
        await i.response.send_message(f"**{kind} spoiler:** ||{safe}||",
                                      allowed_mentions=discord.AllowedMentions.none())


async def setup(bot):
    await bot.add_cog(Community(bot))
