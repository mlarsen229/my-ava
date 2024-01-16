import os
from dotenv import load_dotenv
from twitchio.ext import commands as twitch_commands
from twitchio import Channel
from helpers import Memory, get_listen_input
from processing import process_input, process_output, process_queue_input, process_queue_output, get_bot_response, process_bg_output
from chatbot import Chatbot
from dotenv import load_dotenv
import os
from config_module import ConfigManager, config_store, config_to_dict
import logging
import time
from sentience_module import baseline_sentience
import asyncio

logging.basicConfig(level=logging.INFO)

load_dotenv()
TWITCH_CLIENT_ID = os.getenv("TWITCH_CLIENT_ID")
TWITCH_BOT_NICK = os.getenv("TWITCH_BOT_NICK")
TWITCH_TOKEN = os.getenv("TWITCH_TOKEN")
TWITCH_BOT_PREFIX = "!"

class TwitchBot(twitch_commands.Bot):    
    def __init__(self, config: ConfigManager, loop, chatbot: Chatbot, memory: Memory):
        if config.channel is not None:
            channel = config.channel
        else:
            channel = "biggoronoron"
        time.sleep(2)
        super().__init__(
            token=TWITCH_TOKEN,
            client_id=TWITCH_CLIENT_ID,
            nick=TWITCH_BOT_NICK,
            prefix=TWITCH_BOT_PREFIX,
            initial_channels=[channel],
        )
        self.loop = loop
        self.config = config
        self.memory = memory
        self.chatbot = chatbot
        self.admin_names = [self.config.channel, self.config.user]
        self.special_admin_names = [self.config.channel, self.config.user]
        self.is_running = True

    async def engage_sentience(self):
        print(f"<<<<<<<<<<<<<<<<<< SENTIENCE ENGAGED IN {self.config.name} TWITCHBOT >>>>>>>>>>>>>>>>>>>>>>>> ")
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

    async def event_ready(self):
        print(f"Starting twitch bot {self.config.name}")
        if 'sentience' in self.config.plugins:
            if 'standard' in self.config.bot_type:
                return
            elif 'discord' in self.config.bot_type:
                return
            await self.engage_sentience()

    def close_loop(self):
        loop = self.loop
        if loop.is_running():
            loop.stop()
        while loop.is_running():
            time.sleep(0.1)
        loop.close()

    def shutdown_bot(self):
        self.is_running = False
        self.close_loop()

    async def event_custom_reward(self, data: dict, message_content, username):
        channel = self.get_channel(self.config.channel)
        custom_reward_id_start = data.find("custom-reward-id=") + len("custom-reward-id=")
        custom_reward_id_end = data.find(";", custom_reward_id_start)
        reward_id = data[custom_reward_id_start:custom_reward_id_end]
        if reward_id == self.config.chat_reward_id:
            print("custom chat reward has been called")
            await self.handle_chat_command("twitch", username, message_content, channel)
        elif reward_id == self.config.tts_reward_id:
            print("custom tts reward has been called")
            await self.handle_tts_command("twitch", username, message_content, channel)
        elif reward_id == self.config.queue_reward_id:
            print("custom queue reward has been called")
            await self.handle_queue_command("twitch", username, message_content, channel)
        elif reward_id == self.config.background_reward_id:
            print("custom background reward has been called")
            await self.handle_background_command("twitch", username, message_content, channel)
        elif any(admin_name in username for admin_name in self.admin_names):
            if f"{self.config.name} set chat reward id" in data:
                self.config.chat_reward_id = reward_id
                print(f"Updated self.config.chat_reward_id to {self.config.chat_reward_id}")
                serialized_config = config_to_dict(self.config)
                await channel.send(f"[{self.config.name}]: chat reward id set.")
                config_store[self.config.name] = serialized_config
            elif f"{self.config.name} set tts reward id" in data:
                self.config.tts_reward_id = reward_id
                print(f"Updated self.config.tts_reward_id to {self.config.tts_reward_id}")
                serialized_config = config_to_dict(self.config)
                await channel.send(f"[{self.config.name}]: tts reward id set.")
                config_store[self.config.name] = serialized_config
            elif f"{self.config.name} set queue reward id" in data:
                self.config.queue_reward_id = reward_id
                print(f"Updated self.config.queue_reward_id to {self.config.queue_reward_id}")
                serialized_config = config_to_dict(self.config)
                await channel.send(f"[{self.config.name}]: queue reward id set.")
                config_store[self.config.name] = serialized_config
            elif f"{self.config.name} set background reward id" in data:
                self.config.background_reward_id = reward_id
                print(f"Updated self.config.background_reward_id to {self.config.background_reward_id}")
                serialized_config = config_to_dict(self.config)
                await channel.send(f"[{self.config.name}]: background reward id set.")
                config_store[self.config.name] = serialized_config

    async def event_raw_data(self, data: str):
        if self.config.tts_command_bits == None:
            self.config.tts_command_bits = 0
        if self.config.chat_command_bits ==None:
            self.config.chat_command_bits = 0
        if self.config.queuecost == None:
            self.config.queuecost = 0
        if self.config.bgcost == None:
            self.config.bgcost = 0
        if 'PRIVMSG' in data:
            #print(f"data: {data}")
            channel = self.get_channel(self.config.channel)
            username = data.split('!')[0][1:]
            message_content = data.split('PRIVMSG', 1)[1].split(':', 1)[1]
            #print(f"message_content: {message_content}")
            if 'StreamElements' in username:
                return
            elif "custom-reward-id" in data:
                await self.event_custom_reward(data, message_content, username) 
                return
            elif int(self.config.queuecost) == 0 and '!queue' in message_content:
                await self.handle_queue_command("twitch", username, message_content, channel)
                return
            elif int(self.config.bgcost) == 0 and '!background' in message_content:
                await self.handle_background_command("twitch", username, message_content, channel)
                return   
            elif int(self.config.tts_command_bits) == 0 and f"!{self.config.name}tts" in message_content:
                await self.handle_tts_command("twitch", username, message_content, channel)
                return
            elif int(self.config.chat_command_bits) == 0 and f"!{self.config.name}" in message_content:
                await self.handle_chat_command("twitch", username, message_content, channel)  
                return 
            elif any(admin_name in username for admin_name in self.admin_names):
                if f"!{self.config.name}tts" in message_content:
                    await self.handle_tts_command("twitch", username, message_content, channel)
                    return
                elif f"!{self.config.name}" in message_content:
                    await self.handle_chat_command("twitch", username, message_content, channel)
                    return
                elif '!queue' in message_content:
                    await self.handle_queue_command("twitch", username, message_content, channel)
                    return
                elif '!background' in message_content:
                    await self.handle_background_command("twitch", username, message_content, channel)
                    return
            else:
                if "bits=" in data:
                    bits_cheered = int(data.split('bits=')[1].split(';')[0])
                    if 'queue' in self.config.plugins and bits_cheered >= int(self.config.queuecost) and '!queue' in message_content:
                        await self.handle_queue_command("twitch", username, message_content, channel)
                        return
                    if 'background' in self.config.plugins and bits_cheered >= int(self.config.bgcost) and '!background' in message_content:
                        await self.handle_background_command("twitch", username, message_content, channel)
                        return
                    if bits_cheered >= int(self.config.tts_command_bits) and f"!{self.config.name}tts" in message_content:
                        await self.handle_tts_command("twitch", username, message_content, channel)
                        return
                    elif bits_cheered >= int(self.config.chat_command_bits) and f"!{self.config.name}" in message_content:
                        await self.handle_chat_command("twitch", username, message_content, channel)
                        return
                return     
    
    async def handle_chat_command(self, response_platform, username=None, message=None, channel: Channel=None):
        if response_platform == "twitch":
            message_content = f"Username and username info: '{username}'. Message: {message}"
            combined_context = await process_input(message_content, self.memory, self.chatbot, self.config)
            bot_response = await get_bot_response(message_content, combined_context, self.chatbot, self.config)
            await process_output(response_platform, bot_response, message_content, channel, None, self.chatbot, self.memory, self.config)

    async def handle_tts_command(self, response_platform, username=None, message=None, channel: Channel=None):
        if response_platform == "twitch":
            message_content = f"Username and username info: '{username}'. Message: {message}"
            combined_context = await process_input(f"!tts {message_content}", self.memory, self.chatbot, self.config)
            bot_response = await get_bot_response(message_content, combined_context, self.chatbot, self.config)
            await process_output(response_platform, bot_response, f"!tts {message_content}", channel, None, self.chatbot, self.memory, self.config)

    async def handle_listen_command(self, response_platform):
        if response_platform == "twitch":
            channel = self.get_channel(self.config.channel)
            user_input = await get_listen_input(self.config)
            combined_context = await process_input(f"!tts {user_input}", self.memory, self.chatbot, self.config)
            bot_response = await get_bot_response(user_input, combined_context, self.chatbot, self.config)
            await process_output(response_platform, bot_response, f"!tts {user_input}", channel, None, self.chatbot, self.memory, self.config)

    async def handle_queue_command(self, response_platform, username=None, message=None, channel: Channel=None):
        if response_platform == "twitch":
            queue_prompt = "You maintain a simple queue for interactive viewer events. This entails keeping a list of viewers' names in order by when they are added to the list. People will usually add themselves by using your command ('!queue') and saying nothing else. Whenever you are asked, you will either add somebody to the queue, advance the queue, or display the queue. When asked to add somebody to the queue (or if someone leaves their message body empty and just puts the !queue command into chat), add that person to the next available position in the queue and display the whole queue in your response. When asked to advance the queue, remove the person at the top and send the new queue in your response. Sometimes people will request to be added simply by using your command and not including a message in the body, in these cases please add them to the queue. When asked to display the queue, send the entire queue without making any changes to it. You should send the entire queue every response no matter what. When displaying the queue, always remember not to leave anyone out. Make sure the whole entire queue is displayed and make sure that you do not forget anybody. To cut down on duplicate actions, if people try to remove people, add people, or advance the queue quickly in succession (less than one minute apart) only do it once. If the message portion of a user's input is left out, just add them to the queue. This happens because people just put '!queue' into the chat. Only allow users to be in the queue once at a time. "
            message_content = f"Username and username info: '{username}'. Message: {message}"
            combined_context = await process_queue_input(message_content, self.memory, self.chatbot, self.config)
            bot_response = await get_bot_response(message_content, f"{queue_prompt} {combined_context}", self.chatbot, self.config)
            await process_queue_output(bot_response, combined_context, channel, self.chatbot, self.memory, self.config)

    async def handle_background_command(self, response_platform, username=None, message=None, channel: Channel=None):
        if response_platform == "twitch":
            channel = self.get_channel(self.config.channel)
            message_content = f"Username and username info: '{username}'. Message: {message}"
            background_context = "You help maintain the background image for a stream via your word dictations. Please create a short description in under 400 characters for the attached user's request for a background. Your response should contain nothing but the background description. UNDER NO CIRCUMSTANCES SHOULD YOUR RESPONSE EXCEED 400 CHARACTERS"
            background_prompt = await get_bot_response(f"{background_context} {message_content}", None, self.chatbot, self.config)
            await process_bg_output(background_prompt, channel, self.config, self.chatbot)