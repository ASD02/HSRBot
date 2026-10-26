import logging

from .bot import HSRBot
from .config import Config

logging.basicConfig(level=logging.INFO)
cfg = Config.load()
HSRBot(cfg).run(cfg.token)
