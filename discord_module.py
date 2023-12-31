import discord
from discord.ext import commands
from helpers import Memory, display_file, get_listen_input
from processing import process_input, process_output, get_bot_response
from chatbot import Chatbot
from dotenv import load_dotenv
import os
from config_module import ConfigManager
import logging

logging.basicConfig(level=logging.INFO)

load_dotenv()
DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")

intents = discord.Intents.default()
intents.message_content = True
intents.typing = False
intents.presences = False

class DiscordBot(commands.Bot):
    def __init__(self, loop, config: ConfigManager, chatbot: Chatbot, memory: Memory, *args, **kwargs):
        super().__init__(command_prefix="!", intents=intents, *args, **kwargs)
        logging.info("Initializing DiscordBot")
        self.loop = loop
        self.config = config
        self.memory = memory
        self.chatbot = chatbot
        self.admin_names = ['']
        self.special_admin_names = ['']

    async def start(self):
        await super().start(DISCORD_TOKEN)

    def stop(self):
        try:
            self.loop.stop()
        except Exception as e:
            print(f"error stopping bot: {e}")

    async def on_ready(self):
        print(f"Logged in as {self.config.name}")

    async def on_message(self, ctx):
        if ctx.content.startswith(f"!{self.config.name}"):
            await self.handle_chat_command(ctx)
    
    async def handle_chat_command(self, ctx):
        channel = ctx.channel
        message_content = ctx.content
        combined_context, avatar_context = await process_input(message_content, self.memory, self.chatbot, self.config)
        bot_response = await get_bot_response(message_content, channel, combined_context, self.chatbot)
        await channel.send(f"[{self.config.name}]: {bot_response}")  # Sending to the channel from which the command originated
        avatar_image = await process_output(avatar_context, bot_response, message_content, channel, self.chatbot, self.memory, self.config)
        if 'avatar' in self.config.plugins:
            await channel.send(file=discord.File(avatar_image))  # Sending the avatar image 

    async def handle_listen_command(self):
        channel = ""
        user_input = await get_listen_input(self.config)
        combined_context, avatar_context = await process_input(f"!tts {user_input}", channel, self.memory, self.chatbot, self.config)
        bot_response = await get_bot_response(user_input, combined_context, self.chatbot)
        avatar_image = await process_output(avatar_context, bot_response, f"!tts {user_input}", channel, self.chatbot, self.memory, self.config)
        if 'avatar' in self.config.plugins:
            display_file(avatar_image, self.config.name, 'avatar')