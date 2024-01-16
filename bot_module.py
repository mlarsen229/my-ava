from helpers import Memory, get_chat_input, get_listen_input
from config_module import ConfigManager
from chatbot import Chatbot
from processing import process_input, process_output, get_bot_response
import asyncio
import time
import logging
from sentience_module import baseline_sentience
import traceback

logging.basicConfig(level=logging.INFO)


class StandardBot:
    def __init__(self, config: ConfigManager, loop, chatbot: Chatbot, memory: Memory):
        print("Initializing StandardBot")
        self.loop = loop
        self.config = config
        self.memory = memory
        self.chatbot = chatbot
        self.is_running = True

    async def start(self):
        print(f"Starting standard bot {self.config.name}")
        if 'sentience' in self.config.plugins:
            await self.engage_sentience()
        await self.listen_for_chat()
        while self.is_running:
            await asyncio.sleep(1)

    async def listen_for_chat(self):
        while self.is_running:
            user_input = input('User: ')
            if user_input == 'exit':  # Implement a way to exit
                self.shutdown_bot()
                break
            await self.handle_chat_command(user_input=user_input)
    
    async def engage_sentience(self):
        minute_count = 0
        subconscious_log = " "
        while self.is_running:
            if minute_count % 6 == 0:
                results = await baseline_sentience(subconscious_log, "conscious", self.chatbot, self.memory, self.config)
                subconscious_log = " "
                self.memory.add_sentience(f"BASELINE SENTIENCE LOG: '{results}'. ")
            else:
                results = await baseline_sentience(subconscious_log, "subconscious", self.chatbot, self.memory, self.config)
                subconscious_log += results
            minute_count = (minute_count + 1) % 6
            await asyncio.sleep(600)

    def shutdown_bot(self):
        try:
            self.shutdown()
            self.close_loop()
        except Exception as e:
            print(f"error stopping bot: {e}")

    def shutdown(self):
        print("Shutting down StandardBot")
        self.is_running = False

    def close_loop(self):
        loop = self.loop
        if loop.is_running():
            loop.stop()
        while loop.is_running():
            time.sleep(0.1)
        loop.close()
    
    async def handle_chat_command(self, response_platform="standard", user_input="None"):
        try:
            if response_platform == "standard":
                if user_input == "None":
                    user_input = await get_chat_input(self.config)
                combined_context = await process_input(user_input, self.memory, self.chatbot, self.config) 
                bot_response = await get_bot_response(user_input, combined_context, self.chatbot, self.config)
                await process_output(response_platform, bot_response, user_input, None, None, self.chatbot, self.memory, self.config)
                await self.listen_for_chat()
        except Exception as e:
            print(f"Error in {self.config.name} handle_chat_command(): {e} ")
            traceback.print_exc()

    async def handle_listen_command(self, response_platform):
        if response_platform == "standard":
            user_input = await get_listen_input(self.config)
            combined_context = await process_input(f"!tts {user_input}", self.memory, self.chatbot, self.config)
            bot_response = await get_bot_response(user_input, combined_context, self.chatbot, self.config)
            await process_output(response_platform, bot_response, f"!tts {user_input}", None, None, self.chatbot, self.memory, self.config)