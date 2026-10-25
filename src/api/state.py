from src.app import RagApp
from . import config

rag = RagApp(config.STRATEGIES, config.DEFAULT_STRATEGY)   # one shared instance