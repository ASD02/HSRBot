import discord
from discord import app_commands
from discord.ext import commands

ELEMENT_COLORS = {
    "Physical": 0xC8C8C8, "Fire": 0xE8532B, "Ice": 0x5BC0EB, "Lightning": 0xB05FD6,
    "Wind": 0x4FD6A4, "Quantum": 0x5B4FD6, "Imaginary": 0xF2D544,
}


def info_embed(item: dict, kind: str) -> discord.Embed:
    e = discord.Embed(title=item.get("name", "?"), color=ELEMENT_COLORS.get(item.get("element"), 0x888888))
    e.add_field(name="Rarity", value="★" * int(item.get("rarity", 0)) or "?")
    e.add_field(name="Path", value=item.get("path", "?"))
    if kind == "character":
        e.add_field(name="Element", value=item.get("element", "?"))
    return e


class Lookup(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    def _ac(self, kind):
        async def ac(i: discord.Interaction, current: str):
            return [app_commands.Choice(name=x["name"][:100], value=x["name"][:100])
                    for x in self.bot.game_data.search(kind, current)]
        return ac

    async def _show(self, i, kind, name):
        item = self.bot.game_data.get(kind, name)
        if not item:
            hits = self.bot.game_data.search(kind, name, 5)
            hint = f" Did you mean: {', '.join(h['name'] for h in hits)}?" if hits else ""
            return await i.response.send_message(f"No match for {name!r}.{hint}", ephemeral=True)
        await i.response.send_message(embed=info_embed(item, kind))

    @app_commands.command(description="Look up a character")
    async def character(self, i: discord.Interaction, name: str):
        await self._show(i, "character", name)

    @app_commands.command(description="Look up a Light Cone")
    async def lightcone(self, i: discord.Interaction, name: str):
        await self._show(i, "lightcone", name)

    @character.autocomplete("name")
    async def _char_ac(self, i, current):
        return await self._ac("character")(i, current)

    @lightcone.autocomplete("name")
    async def _lc_ac(self, i, current):
        return await self._ac("lightcone")(i, current)

    @app_commands.command(description="Refresh game data from the community dataset (bot owner)")
    async def refreshdata(self, i: discord.Interaction):
        if not await self.bot.is_owner(i.user):
            return await i.response.send_message("Owner only.", ephemeral=True)
        await i.response.defer(ephemeral=True)
        await self.bot.game_data.load(self.bot.session, force=True)
        gd = self.bot.game_data
        await i.followup.send(f"Loaded {len(gd.characters)} characters, {len(gd.light_cones)} light cones.")


async def setup(bot):
    await bot.add_cog(Lookup(bot))
