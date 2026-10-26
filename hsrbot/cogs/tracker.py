import discord
from discord import app_commands
from discord.ext import commands

from ..warp_tracker import BANNER_TYPES, WarpImportError, compute_history, fetch_all, parse_authkey_url


class Warp(app_commands.Group):
    def __init__(self, cog):
        super().__init__(name="warp", description="Warp history tracker", guild_only=False)
        self.cog = cog

    @app_commands.command(name="import", description="Import your history from the in-game Warp History link")
    async def import_(self, i: discord.Interaction, url: str):
        try:
            params = parse_authkey_url(url)
        except ValueError as e:
            return await i.response.send_message(str(e), ephemeral=True)
        await i.response.defer(ephemeral=True)
        try:
            records = await fetch_all(self.cog.bot.session, params)
        except WarpImportError as e:
            return await i.followup.send(str(e), ephemeral=True)
        db, new = self.cog.bot.db, 0
        for r in records:
            new += await db.execute("INSERT OR IGNORE INTO warp_records VALUES (?,?,?,?,?,?)",
                                    (i.user.id, r["record_id"], r["banner"], r["item"], r["rarity"], r["time"]))
        await i.followup.send(f"Imported {new} new records ({len(records)} fetched).", ephemeral=True)

    @app_commands.command(description="Pity, 50/50 results, luck and Jade spent per banner")
    @app_commands.choices(banner=[app_commands.Choice(name=k, value=k) for k in BANNER_TYPES.values()])
    async def stats(self, i: discord.Interaction, banner: str = "character"):
        rows = await self.cog.bot.db.fetchall(
            "SELECT * FROM warp_records WHERE user_id=? AND banner=?", (i.user.id, banner))
        s = compute_history([dict(r) for r in rows]).get(banner)
        if not s:
            return await i.response.send_message("No records. Use /warp import first.", ephemeral=True)
        e = discord.Embed(title=f"{banner} banner")
        e.add_field(name="Pulls", value=f"{s['total']} ({s['jade']:,} Jade)")
        e.add_field(name="Current pity", value=s["pity"])
        if s["luck"] is not None:
            e.add_field(name="Luck", value=f"luckier than {s['luck']:.0%} of pulls")
        e.add_field(name="5-stars", inline=False, value="\n".join(
            f"{f['item']} @ {f['pity']}{' (lost 50/50)' if f['lost_5050'] else ''}" for f in s["fives"][-15:]) or "none yet")
        await i.response.send_message(embed=e, ephemeral=True)

    @app_commands.command(description="Delete your stored warp records")
    async def clear(self, i: discord.Interaction):
        n = await self.cog.bot.db.execute("DELETE FROM warp_records WHERE user_id=?", (i.user.id,))
        await i.response.send_message(f"Deleted {n} records.", ephemeral=True)


class Tracker(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        bot.tree.add_command(Warp(self))

    def cog_unload(self):
        self.bot.tree.remove_command("warp")


async def setup(bot):
    await bot.add_cog(Tracker(bot))
