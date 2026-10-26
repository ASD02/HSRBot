from datetime import datetime, timezone

import discord
from discord import app_commands
from discord.ext import commands

from ..enka import EnkaError, Profile, fetch_profile
from ..i18n import tr
from ..relics import SLOT_NAMES, relic_subs, score_relic, weights_for
from ..uid import validate_uid

STATS = {"achievements": "Achievements", "characters": "Characters owned", "level": "Trailblaze Level"}


def rank_rows(rows, stat: str, limit: int = 10):
    """rows: dicts with user_id and the stat columns. Highest first, missing values dropped."""
    return sorted((r for r in rows if r[stat] is not None), key=lambda r: -r[stat])[:limit]


class ProfileCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    async def _uid_for(self, i, uid: str | None) -> str | None:
        if uid:
            return validate_uid(uid)[0]
        row = await self.bot.db.fetchone("SELECT uid FROM links WHERE user_id=?", (i.user.id,))
        return row["uid"] if row else None

    async def _snapshot(self, user_id: int, p: Profile):
        await self.bot.db.execute(
            "INSERT OR REPLACE INTO snapshots VALUES (?,?,?,?,?,?,?)",
            (user_id, p.uid, datetime.now(timezone.utc).isoformat(), p.achievements, p.characters,
             p.world_level, p.level))

    @app_commands.command(description="Link your UID (the showcase must be public for profile/build)")
    async def link(self, i: discord.Interaction, uid: str):
        try:
            uid, _ = validate_uid(uid)
        except ValueError as e:
            return await i.response.send_message(str(e), ephemeral=True)
        await self.bot.db.execute("INSERT OR REPLACE INTO links VALUES (?,?)", (i.user.id, uid))
        await i.response.send_message(tr(i.locale, "linked", uid=uid), ephemeral=True)

    @app_commands.command(description="Show a player profile and showcase")
    async def profile(self, i: discord.Interaction, uid: str | None = None):
        try:
            uid = await self._uid_for(i, uid)
        except ValueError as e:
            return await i.response.send_message(str(e), ephemeral=True)
        if not uid:
            return await i.response.send_message(tr(i.locale, "not_linked"), ephemeral=True)
        await i.response.defer()
        try:
            p = await fetch_profile(self.bot.session, uid)
        except EnkaError as e:
            return await i.followup.send(str(e))
        link = await self.bot.db.fetchone("SELECT user_id FROM links WHERE user_id=? AND uid=?", (i.user.id, uid))
        if link:
            await self._snapshot(i.user.id, p)
        e = discord.Embed(title=f"{p.nickname} ({p.uid})")
        e.add_field(name="Trailblaze Level", value=p.level)
        e.add_field(name="Equilibrium Level", value=p.world_level)
        e.add_field(name="Achievements", value=p.achievements if p.achievements is not None else "private")
        e.add_field(name="Characters", value=p.characters if p.characters is not None else "private")
        chars = self.bot.game_data.characters
        shown = [f"{chars.get(str(a.get('avatarId')), {}).get('name', '#' + str(a.get('avatarId')))} "
                 f"Lv{a.get('level', '?')} E{a.get('rank', 0)}" for a in p.avatars]
        e.add_field(name="Showcase", value="\n".join(shown) or "Showcase is private or empty.", inline=False)
        await i.followup.send(embed=e)

    @app_commands.command(description="Relic breakdown for a showcased character")
    async def build(self, i: discord.Interaction, character: str, uid: str | None = None):
        try:
            uid = await self._uid_for(i, uid)
        except ValueError as e:
            return await i.response.send_message(str(e), ephemeral=True)
        if not uid:
            return await i.response.send_message(tr(i.locale, "not_linked"), ephemeral=True)
        await i.response.defer()
        try:
            p = await fetch_profile(self.bot.session, uid)
        except EnkaError as e:
            return await i.followup.send(str(e))
        gd = self.bot.game_data
        match = next((a for a in p.avatars
                      if gd.characters.get(str(a.get("avatarId")), {}).get("name", "").lower() == character.strip().lower()), None)
        if not match:
            return await i.followup.send(f"{character!r} isn't in {p.nickname}'s showcase.")
        info = gd.characters[str(match["avatarId"])]
        weights = weights_for(info.get("path"))
        lc = gd.light_cones.get(str((match.get("equipment") or {}).get("tid")), {}).get("name", "none")
        e = discord.Embed(title=f"{info['name']} E{match.get('rank', 0)} Lv{match.get('level', '?')}",
                          description=f"Light Cone: {lc}")
        for r in sorted(match.get("relicList") or [], key=lambda r: r.get("type", 0)):
            sc = score_relic(relic_subs(r, gd.relic_sub_affixes), weights)
            flag = f", {sc.wasted} wasted" if sc.wasted else ""
            e.add_field(name=f"{SLOT_NAMES.get(r.get('type'), '?')} +{r.get('level', 0)}",
                        value=f"{sc.efficiency:.0%} roll efficiency{flag}")
        e.set_footer(text="Efficiency uses rough per-Path weights, not an exact build.")
        await i.followup.send(embed=e)

    @build.autocomplete("character")
    async def _build_ac(self, i, current: str):
        return [app_commands.Choice(name=c["name"][:100], value=c["name"][:100])
                for c in self.bot.game_data.search("character", current)]

    @app_commands.command(description="Server leaderboard from linked players' last profile lookups")
    @app_commands.choices(stat=[app_commands.Choice(name=n, value=k) for k, n in STATS.items()])
    @app_commands.guild_only()
    async def leaderboard(self, i: discord.Interaction, stat: str):
        rows = await self.bot.db.fetchall(
            "SELECT s.* FROM snapshots s JOIN (SELECT user_id, MAX(taken_at) m FROM snapshots GROUP BY user_id) x "
            "ON s.user_id=x.user_id AND s.taken_at=x.m")
        mine = []
        for r in rows[:200]:  # fetch, not cache: the Members intent is privileged and off
            try:
                await i.guild.fetch_member(r["user_id"])
            except discord.NotFound:
                continue
            mine.append(dict(r))
        top = rank_rows(mine, stat)
        if not top:
            return await i.response.send_message("No data yet. Link a UID and run /profile.", ephemeral=True)
        await i.response.send_message(
            f"**{STATS[stat]}**\n" + "\n".join(f"{n}. <@{r['user_id']}>: {r[stat]}" for n, r in enumerate(top, 1)),
            allowed_mentions=discord.AllowedMentions.none())


async def setup(bot):
    await bot.add_cog(ProfileCog(bot))
