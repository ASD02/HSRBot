import logging
import pkgutil

import aiohttp
import discord
from discord.ext import commands

from . import cogs
from .config import Config
from .data import GameData
from .db import Database

log = logging.getLogger("hsrbot")


class HSRBot(commands.Bot):
    def __init__(self, config: Config):
        super().__init__(command_prefix=commands.when_mentioned, intents=discord.Intents.default())
        self.config = config
        self.db = Database(config.db_path)
        self.session: aiohttp.ClientSession | None = None
        self.game_data = GameData(config.data_dir)

    async def setup_hook(self) -> None:
        await self.db.connect()
        self.session = aiohttp.ClientSession()
        await self.game_data.load(self.session)
        for mod in pkgutil.iter_modules(cogs.__path__):
            await self.load_extension(f"{cogs.__name__}.{mod.name}")
        if self.config.dev_guild:
            guild = discord.Object(self.config.dev_guild)
            self.tree.copy_global_to(guild=guild)
            await self.tree.sync(guild=guild)
        else:
            await self.tree.sync()

    async def close(self) -> None:
        if self.session:
            await self.session.close()
        await self.db.close()
        await super().close()
