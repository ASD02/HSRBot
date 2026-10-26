import logging
from datetime import datetime, timedelta, timezone

import discord
from discord import app_commands
from discord.ext import commands, tasks

from ..schedule import REGIONS, current_and_next, due_reminders, load_schedule, next_reset

log = logging.getLogger("hsrbot.calendar")
REGION_CHOICES = [app_commands.Choice(name=r, value=r) for r in REGIONS]


def ts(dt: datetime, style: str = "R") -> str:
    return f"<t:{int(dt.timestamp())}:{style}>"


class Calendar(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.schedule = load_schedule(bot.config.data_dir / "schedule.json")
        self.remind.start()

    def cog_unload(self):
        self.remind.cancel()

    def _note(self) -> str:
        return "\n*Dates are estimates; edit `data/schedule.json` when HoYoverse confirms.*" if self.schedule.estimated else ""

    @app_commands.command(description="Current and upcoming banner phases")
    @app_commands.choices(region=REGION_CHOICES)
    async def banners(self, i: discord.Interaction, region: str = "Asia"):
        cur, nxt = current_and_next(self.schedule, datetime.now(timezone.utc), REGIONS[region])
        lines = []
        if cur:
            lines.append(f"**Now:** v{cur[0]} phase {cur[1]}, ends {ts(cur[3])}")
        if nxt:
            lines.append(f"**Next:** v{nxt[0]} phase {nxt[1]}, starts {ts(nxt[2])}")
        if not lines:
            lines.append("No upcoming phases in the schedule file.")
        await i.response.send_message("\n".join(lines) + self._note())

    @app_commands.command(description="Countdowns to each endgame mode reset")
    @app_commands.choices(region=REGION_CHOICES)
    async def resets(self, i: discord.Interaction, region: str = "Asia"):
        now = datetime.now(timezone.utc)
        rows = sorted((next_reset(m, now, REGIONS[region]), m.name) for m in self.schedule.modes)
        await i.response.send_message(
            "\n".join(f"**{n}**: {ts(t)} ({ts(t, 'f')})" for t, n in rows) + self._note())

    @tasks.loop(minutes=10)
    async def remind(self):
        now = datetime.now(timezone.utc)
        for guild in self.bot.guilds:
            chan_id = await self.bot.db.get_conf(guild.id, "announce_channel")
            if not chan_id or not (chan := guild.get_channel(int(chan_id))):
                continue
            region = await self.bot.db.get_conf(guild.id, "region") or "Asia"
            role = await self.bot.db.get_conf(guild.id, "ping_role")
            for label, when in due_reminders(self.schedule, now, REGIONS.get(region, 8)):
                if await self.bot.db.mark_sent(f"{guild.id}:{label}:{when.isoformat()}"):
                    ping = f"<@&{role}> " if role else ""
                    try:
                        await chan.send(f"{ping}**{label}** {ts(when)}",
                                        allowed_mentions=discord.AllowedMentions(roles=True))
                    except discord.HTTPException as e:
                        log.warning("reminder failed in %s: %s", guild.id, e)

    @remind.before_loop
    async def _wait(self):
        await self.bot.wait_until_ready()


async def setup(bot):
    await bot.add_cog(Calendar(bot))
