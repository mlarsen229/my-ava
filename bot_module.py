from helpers import Memory, get_listen_input
from config_module import ConfigManager
from chatbot import Chatbot
from twitch_module import TwitchBot
from processing import process_input, process_output, get_bot_response
import os
from dotenv import load_dotenv
from discord_module import DiscordBot
import asyncio

load_dotenv()
TWITCH_CLIENT_ID = os.getenv("TWITCH_CLIENT_ID")
TWITCH_BOT_NICK = os.getenv("TWITCH_BOT_NICK")
TWITCH_BOT_PREFIX = "!"

bot_instance = None


#Specify platform here. Insert your desired bot class based on your desired platform (config.bot_type)
def create_bot(loop, config: ConfigManager, chatbot: Chatbot, memory: Memory):
    if config.bot_type == 'twitch':
        bot_type = TwitchBot
    elif config.bot_type == 'discord':
        bot_type = DiscordBot
    else:
        bot_type = StandardBot
    bot_instance = bot_type(loop, config, chatbot, memory)
    return bot_instance


#This is a plain bot class to which your desired platform's endpoints can be plugged into
class StandardBot:
    def __init__(self, loop, config: ConfigManager, chatbot: Chatbot, memory: Memory):
        print("Initializing Standard AVA")
        self.loop = loop
        self.config = config
        self.memory = memory
        self.chatbot = chatbot
        self.is_running = True

    async def start(self):
        print(f"starting standard AVA {self.config.name}")
        await self.await_chat_input(self)
        while self.is_running:
            await asyncio.sleep(1)

    def stop(self):
        try:
            self.shutdown()
            self.loop.stop()
        except Exception as e:
            print(f"error stopping bot: {e}")

    def shutdown(self):
        print("Shutting down StandardBot")
        self.is_running = False

    async def await_chat_input(self):
        #implement your own frontend for fetching inputs
        user_input = input("User: ")
        print(f"User: {user_input}")
        await self.handle_chat_command(user_input)
    
    async def handle_chat_command(self, user_input):
        channel = ""
        combined_context, avatar_context = await process_input(user_input, channel, self.memory, self.chatbot, self.config) 
        print(f"combined_context: {combined_context}")
        bot_response = await get_bot_response(user_input, combined_context, self.chatbot)
        await process_output(avatar_context, bot_response, user_input, channel, self.chatbot, self.memory, self.config)
        await self.await_chat_input(self)

    async def handle_listen_command(self):
        channel = ""
        user_input = await get_listen_input(self.config)
        combined_context, avatar_context = await process_input(f"!tts {user_input}", channel, self.memory, self.chatbot, self.config)
        bot_response = await get_bot_response(user_input, combined_context, self.chatbot)
        await process_output(avatar_context, bot_response, f"!tts {user_input}", channel, self.chatbot, self.memory, self.config)