import discord
from discord import app_commands
from discord.ext import commands

from .. import speed as sp


class Speed(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(description="Action Value for a speed, and actions per cycle count")
    async def av(self, i: discord.Interaction, spd: app_commands.Range[float, 1, 1000],
                 cycles: app_commands.Range[int, 1, 10] = 5):
        rows = "\n".join(f"Cycle {c}: {sp.actions_in(spd, c)} actions" for c in range(1, cycles + 1))
        await i.response.send_message(f"**{spd:g} SPD** = {sp.av(spd):.2f} AV per action\n{rows}")

    @app_commands.command(description="Minimum SPD to get N actions within M cycles")
    async def breakpoint(self, i: discord.Interaction, actions: app_commands.Range[int, 1, 20],
                         cycles: app_commands.Range[int, 1, 10]):
        need = sp.min_speed(actions, cycles)
        await i.response.send_message(
            f"**{actions} actions in {cycles} cycle(s)** ({sp.cycle_budget(cycles)} AV) needs "
            f"**{need:.2f} SPD** (so {int(need) + 1 if need % 1 else int(need)} in-game)")

    @app_commands.command(description="Turn order, e.g. units: Seele:134, Bronya:99")
    async def turnorder(self, i: discord.Interaction, units: str,
                        actions: app_commands.Range[int, 1, 30] = 10):
        try:
            order = sp.turn_order(sp.parse_units(units), actions)
        except ValueError as e:
            return await i.response.send_message(str(e), ephemeral=True)
        lines = [f"{n}. {name} @ {t:.1f} AV" for n, (name, t) in enumerate(order, 1)]
        await i.response.send_message("\n".join(lines))


async def setup(bot):
    await bot.add_cog(Speed(bot))
