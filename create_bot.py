from helpers import Memory
from config_module import ConfigManager
from chatbot import Chatbot
from twitch_module import TwitchBot
from discord_module import DiscordBot
from bot_module import StandardBot
import asyncio

bot_instance = None

def create_bot(config: ConfigManager, chatbot: Chatbot, memory: Memory):
    bots = []
    loops = []
    if 'twitch' in config.bot_type:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        loops.append(loop)
        bots.append(TwitchBot(config, loop, chatbot, memory))
    if 'standard' in config.bot_type:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        loops.append(loop)
        bots.append(StandardBot(config, loop,chatbot, memory))
    if 'discord' in config.bot_type:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        loops.append(loop)
        bots.append(DiscordBot(config, loop, chatbot, memory))
    return bots, loops