import random

import discord
from discord import app_commands
from discord.ext import commands

from ..trivia import Question, make_question


class QuizView(discord.ui.View):
    def __init__(self, q: Question):
        super().__init__(timeout=30)
        self.q, self.tried, self.done = q, set(), False
        for opt in q.options:
            btn = discord.ui.Button(label=opt[:80], style=discord.ButtonStyle.secondary)
            btn.callback = self._make_cb(opt)
            self.add_item(btn)

    def _make_cb(self, opt):
        async def cb(i: discord.Interaction):
            if self.done:
                return await i.response.send_message("Already solved.", ephemeral=True)
            if i.user.id in self.tried:
                return await i.response.send_message("You already guessed.", ephemeral=True)
            self.tried.add(i.user.id)
            if opt != self.q.answer:
                return await i.response.send_message("Not quite!", ephemeral=True)
            self.done = True
            for b in self.children:
                b.disabled = True
            await i.response.edit_message(
                content=f"{self.q.prompt}\n✅ **{self.q.answer}**, solved by {i.user.mention}", view=self)
        return cb

    async def on_timeout(self):
        self.done = True


class Fun(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    async def _ask(self, i: discord.Interaction, kind: str | None):
        q = make_question(self.bot.game_data.characters, random.Random(), kind)
        if not q:
            return await i.response.send_message("Not enough game data loaded yet.", ephemeral=True)
        await i.response.send_message(q.prompt, view=QuizView(q), allowed_mentions=discord.AllowedMentions.none())

    @app_commands.command(description="Random HSR trivia question")
    async def trivia(self, i: discord.Interaction):
        await self._ask(i, None)

    @app_commands.command(description="Guess the character from hints")
    async def guess(self, i: discord.Interaction):
        await self._ask(i, "guess")


async def setup(bot):
    await bot.add_cog(Fun(bot))
