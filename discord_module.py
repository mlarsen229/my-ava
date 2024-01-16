import discord
from discord.ext import commands
from helpers import Memory, get_listen_input
from processing import process_input, process_output, get_bot_response
from chatbot import Chatbot
from dotenv import load_dotenv
import os
from config_module import ConfigManager
import logging
import asyncio
from sentience_module import baseline_sentience

logging.basicConfig(level=logging.INFO)

load_dotenv()
DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")

intents = discord.Intents.default()
intents.message_content = True
intents.typing = False
intents.presences = False

class DiscordBot(commands.Bot):
    def __init__(self, config: ConfigManager, loop, chatbot: Chatbot, memory: Memory, *args, **kwargs):
        super().__init__(command_prefix="!", intents=intents, *args, **kwargs)
        logging.info("Initializing DiscordBot")
        self.loop = loop
        self.config = config
        self.memory = memory
        self.chatbot = chatbot
        self.admin_names = [self.config.user]
        self.special_admin_names = [self.config.user]
        self.is_running = True

    async def start(self):
        await super().start(DISCORD_TOKEN)

    async def engage_sentience(self):
        print(f"<<<<<<<<<<<<<<<<<< SENTIENCE ENGAGED IN {self.config.name} DISCORDBOT >>>>>>>>>>>>>>>>>>>>>>>> ")
        minute_count = 0
        subconscious_log = " "
        while self.is_running:
            if minute_count % 6 == 0:
                results = await baseline_sentience(subconscious_log, "conscious", self.chatbot, self.memory, self.config)
                print(f"<<<<<<<<<<<<<<<<<<<<<<< {self.config.name} CONSCIOUS SENTIENCE RESULTS: {results} >>>>>>>>>>>>>>>>>>>>>>")
                subconscious_log = " "
                self.memory.add_sentience(f"BASELINE SENTIENCE LOG: '{results}'. ")
            else:
                results = await baseline_sentience(subconscious_log, "subconscious", self.chatbot, self.memory, self.config)
                print(f"<<<<<<<<<<<<<<<<<<<<<<< {self.config.name} SUBCONSCIOUS SENTIENCE RESULTS: {results} >>>>>>>>>>>>>>>>>>>>>>")
                subconscious_log += results
            minute_count = (minute_count + 1) % 6
            await asyncio.sleep(600)

    def shutdown_bot(self):
        self.is_running = False
        loop = self.loop
        asyncio.run_coroutine_threadsafe(self.close(), loop)

    async def on_ready(self):
        print(f"Starting discord bot {self.config.name}")
        if 'sentience' in self.config.plugins:
            if 'standard' in self.config.bot_type:
                return
            await self.engage_sentience()

    async def on_message(self, ctx):
        if ctx.content.startswith(f"!{self.config.name}"):
            await self.handle_chat_command("discord", ctx)
    
    async def handle_chat_command(self, response_platform, ctx=None):
        if response_platform == "discord":
            channel = ctx.channel
            message_content = ctx.content
            combined_context = await process_input(message_content, self.memory, self.chatbot, self.config)
            bot_response = await get_bot_response(message_content, combined_context, self.chatbot, self.config)
            await process_output(response_platform, bot_response, message_content, None, channel, self.chatbot, self.memory, self.config)
            
    async def handle_listen_command(self, response_platform):
        if response_platform == "discord":
            channel = ""
            user_input = await get_listen_input(self.config)
            combined_context = await process_input(f"!tts {user_input}", self.memory, self.chatbot, self.config)
            bot_response = await get_bot_response(user_input, combined_context, self.chatbot, self.config)
            await process_output(response_platform, bot_response, f"!tts {user_input}", None, channel, self.chatbot, self.memory, self.config)