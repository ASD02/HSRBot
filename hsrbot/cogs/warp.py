import random

import discord
from discord import app_commands
from discord.ext import commands

from ..gacha import BANNERS, expected_pulls, odds_by_budget, rate, simulate_pull

JADE_PER_PULL = 160
BANNER_CHOICES = [app_commands.Choice(name=b.name, value=k) for k, b in BANNERS.items()]


def format_plan(banner_key: str, pulls: int, pity: int, guaranteed: bool, copies: int) -> str:
    b = BANNERS[banner_key]
    odds = odds_by_budget(b, pulls, pity, guaranteed, copies)
    exp = expected_pulls(b, pity, guaranteed, copies)
    return (f"**{b.name} banner**: {pulls} pulls, pity {pity}, "
            f"{'guaranteed' if guaranteed else '50/50' if banner_key == 'character' else 'no guarantee'}\n"
            f"Chance of {copies} featured: **{odds:.1%}**\n"
            f"Average pulls needed: ~{exp:.0f} ({exp * JADE_PER_PULL:,.0f} Stellar Jade)")


class Warp(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(description="Pity status and odds for a banner")
    @app_commands.choices(banner=BANNER_CHOICES)
    async def pity(self, i: discord.Interaction, banner: str, pity: app_commands.Range[int, 0, 89]):
        b = BANNERS[banner]
        if pity >= b.hard:
            return await i.response.send_message(f"Pity must be 0-{b.hard - 1} on this banner.", ephemeral=True)
        await i.response.send_message(
            f"**{b.name} banner** at pity {pity}\n"
            f"Next pull 5-star rate: **{rate(b, pity):.2%}**\n"
            f"Soft pity at pull {b.soft_start}, hard pity at {b.hard} "
            f"(**{b.hard - pity}** pulls away)\n"
            f"Average pulls to the featured unit: ~{expected_pulls(b, pity, False):.0f} "
            f"(~{expected_pulls(b, pity, True):.0f} if guaranteed)")

    @app_commands.command(description="Odds of landing a featured unit with your current resources")
    @app_commands.choices(banner=BANNER_CHOICES)
    async def pullplan(self, i: discord.Interaction, banner: str,
                       jade: app_commands.Range[int, 0, 1_000_000] = 0,
                       passes: app_commands.Range[int, 0, 5000] = 0,
                       pity: app_commands.Range[int, 0, 89] = 0,
                       guaranteed: bool = False,
                       copies: app_commands.Range[int, 1, 7] = 1):
        pulls = jade // JADE_PER_PULL + passes
        if pity >= BANNERS[banner].hard:
            return await i.response.send_message("Pity is too high for that banner.", ephemeral=True)
        await i.response.send_message(format_plan(banner, pulls, pity, guaranteed, copies))

    @app_commands.command(description="Simulate pulls with the real pity rules")
    @app_commands.choices(banner=BANNER_CHOICES)
    async def warpsim(self, i: discord.Interaction, banner: str,
                      pulls: app_commands.Range[int, 1, 1000] = 10,
                      pity: app_commands.Range[int, 0, 89] = 0,
                      guaranteed: bool = False):
        b = BANNERS[banner]
        if pity >= b.hard:
            return await i.response.send_message("Pity is too high for that banner.", ephemeral=True)
        rng, hits, p, g = random.Random(), [], pity, guaranteed
        for n in range(1, pulls + 1):
            five, feat, p, g = simulate_pull(b, p, g, rng)
            if five:
                hits.append(f"pull {n}: {'⭐ featured' if feat else 'standard (lost 50/50)' if banner == 'character' else 'standard'}")
        body = "\n".join(hits) or "No 5-stars this time."
        await i.response.send_message(f"**{b.name}**, {pulls} pulls from pity {pity}\n{body}\n"
                                      f"Ending pity: {p}{' (guaranteed)' if g else ''}")


async def setup(bot):
    await bot.add_cog(Warp(bot))
