import os
from dotenv import load_dotenv
from twitchio.ext import commands as twitch_commands
from twitchio import Channel
from helpers import Memory, truncate_text, display_file, get_twitch_token, raise_cost, get_listen_input
from processing import process_input, process_output, process_queue_input, process_queue_output, get_bot_response
from chatbot import Chatbot
from dotenv import load_dotenv
import os
from image_module import get_background
from config_module import ConfigManager, save_configs, config_store, config_to_dict
import logging
import time

logging.basicConfig(level=logging.INFO)

load_dotenv()
TWITCH_CLIENT_ID = os.getenv("TWITCH_CLIENT_ID")
TWITCH_BOT_NICK = os.getenv("TWITCH_BOT_NICK")
TWITCH_BOT_PREFIX = "!"


class TwitchBot(twitch_commands.Bot):    
    def __init__(self, loop, config: ConfigManager, chatbot: Chatbot, memory: Memory, user_store, save_users):
        logging.info("Initializing TwitchBot")  # Add this line
        time.sleep(2)
        token = get_twitch_token()
        print(f"twitch token in TwitchBot init: {token}")
        super().__init__(
            token=token,
            client_id=TWITCH_CLIENT_ID,
            nick=TWITCH_BOT_NICK,
            prefix=TWITCH_BOT_PREFIX,
            initial_channels=[config.channel],
        )
        self.loop = loop
        self.config = config
        self.memory = memory
        self.chatbot = chatbot
        self.user_store = user_store
        self.admin_names = [self.config.channel, 'biggoronoron']
        self.save_users = save_users
        self.special_admin_names = ['mistafuzza', 'biggoronoron', 'mattress375']

    async def event_ready(self):
        print(f"Logged in")

    def stop(self):
        try:
            self.loop.stop()
        except Exception as e:
            print(f"error stopping bot: {e}")

    async def event_custom_reward(self, data: dict, message_content, username):
        channel = self.get_channel(self.config.channel)
        custom_reward_id_start = data.find("custom-reward-id=") + len("custom-reward-id=")
        custom_reward_id_end = data.find(";", custom_reward_id_start)
        reward_id = data[custom_reward_id_start:custom_reward_id_end]
        if reward_id == self.config.chat_reward_id:
            print("custom chat reward has been called")
            await self.handle_chat_command(username, message_content, channel)
        elif reward_id == self.config.tts_reward_id:
            print("custom tts reward has been called")
            await self.handle_tts_command(username, message_content, channel)
        elif reward_id == self.config.queue_reward_id:
            print("custom queue reward has been called")
            await self.handle_queue_command(username, message_content, channel)
        elif reward_id == self.config.background_reward_id:
            print("custom background reward has been called")
            await self.handle_background_command(username, message_content, channel)
        elif any(admin_name in username for admin_name in self.admin_names):
            if f"{self.config.name} set chat reward id" in data:
                self.config.chat_reward_id = reward_id
                print(f"Updated self.config.chat_reward_id to {self.config.chat_reward_id}")
                serialized_config = config_to_dict(self.config)
                await channel.send(f"[{self.config.name}]: chat reward id set.")
                config_store[self.config.name] = serialized_config
                save_configs(config_store)
            elif f"{self.config.name} set tts reward id" in data:
                self.config.tts_reward_id = reward_id
                print(f"Updated self.config.chat_reward_id to {self.config.tts_reward_id}")
                serialized_config = config_to_dict(self.config)
                await channel.send(f"[{self.config.name}]: tts reward id set.")
                config_store[self.config.name] = serialized_config
                save_configs(config_store)
            elif f"{self.config.name} set queue reward id" in data:
                self.config.queue_reward_id = reward_id
                print(f"Updated self.config.queue_reward_id to {self.config.queue_reward_id}")
                serialized_config = config_to_dict(self.config)
                await channel.send(f"[{self.config.name}]: queue reward id set.")
                config_store[self.config.name] = serialized_config
                save_configs(config_store)
            elif f"{self.config.name} set background reward id" in data:
                self.config.background_reward_id = reward_id
                print(f"Updated self.config.background_reward_id to {self.config.background_reward_id}")
                serialized_config = config_to_dict(self.config)
                await channel.send(f"[{self.config.name}]: background reward id set.")
                config_store[self.config.name] = serialized_config
                save_configs(config_store)

    async def event_raw_data(self, data: str):
        if self.config.tts_command_bits == None:
            self.config.tts_command_bits = 0
        if self.config.chat_command_bits ==None:
            self.config.chat_command_bits = 0
        if 'PRIVMSG' in data:
            #print(f"data: {data}")
            channel = self.get_channel(self.config.channel)
            username = data.split('!')[0][1:]
            if 'StreamElements' in username:
                return
            message_content = data.split('PRIVMSG', 1)[1].split(':', 1)[1]
            #print(f"message_content: {message_content}")  
            if "custom-reward-id" in data:
                await self.event_custom_reward(data, message_content, username) 
            elif 'queue' in self.config.plugins and int(self.config.queuecost) == 0 and '!queue' in message_content:
                await self.handle_queue_command(username, message_content, channel)
            elif 'background' in self.config.plugins and '!background' in message_content:
                await self.handle_background_command(username, message_content, channel)           
            else:
                if "bits=" in data:
                    bits_cheered = int(data.split('bits=')[1].split(';')[0])
                    if 'queue' in self.config.plugins and bits_cheered >= int(self.config.queuecost) and '!queue' in message_content:
                        await self.handle_queue_command(username, message_content, channel)  
                    if bits_cheered >= int(self.config.tts_command_bits) and f"!{self.config.name}tts" in message_content:
                        await self.handle_tts_command(username, message_content, channel)
                    elif bits_cheered >= int(self.config.chat_command_bits) and f"!{self.config.name}" in message_content:
                        await self.handle_chat_command(username, message_content, channel)            
                elif any(admin_name in username for admin_name in self.admin_names):
                    if f"!{self.config.name}tts" in message_content:
                        await self.handle_tts_command(username, message_content, channel)
                    elif f"!{self.config.name}" in message_content:
                        await self.handle_chat_command(username, message_content, channel)  
                elif int(self.config.tts_command_bits) == 0 and f"!{self.config.name}tts" in message_content:
                        await self.handle_tts_command(username, message_content, channel)
                elif int(self.config.chat_command_bits) == 0 and f"!{self.config.name}" in message_content:
                        await self.handle_chat_command(username, message_content, channel)             
    
    async def handle_chat_command(self, username, message, channel: Channel):
        await raise_cost(self.user_store, self.save_users, self.config)
        message_content = f"Username and username info: '{username}'. Message: {message}"
        combined_context = await process_input(message_content, channel, self.memory, self.chatbot, self.config)
        bot_response = await get_bot_response(message_content, combined_context, self.chatbot)
        truncated_response = truncate_text(bot_response, 485)
        await channel.send(f"[{self.config.name}]: {truncated_response}")
        await process_output(bot_response, message_content, self.chatbot, self.memory, self.config)

    async def handle_tts_command(self, username, message, channel: Channel):
        await raise_cost(self.user_store, self.save_users, self.config)
        message_content = f"Username and username info: '{username}'. Message: {message}"
        combined_context = await process_input(message_content, channel, self.memory, self.chatbot, self.config)
        bot_response = await get_bot_response(message_content, combined_context, self.chatbot)
        truncated_response = truncate_text(bot_response, 485)
        await channel.send(f"[{self.config.name}]: {truncated_response}")
        await process_output(truncated_response, self.chatbot, self.memory)

    async def handle_listen_command(self):
        channel = self.get_channel(self.config.channel)
        await raise_cost(self.user_store, self.save_users, self.config)
        channel = self.get_channel(self.config.channel)
        user_input = await get_listen_input(self.config)
        combined_context = await process_input(user_input, channel, self.memory, self.chatbot, self.config)
        bot_response = await get_bot_response(user_input, combined_context, self.chatbot)
        truncated_response = truncate_text(bot_response, 485)       
        await channel.send(f"[{self.config.name}]: {truncated_response}")   
        await process_output(bot_response, user_input, self.chatbot, self.memory, self.config)

    async def handle_queue_command(self, username, message, channel: Channel):
        await raise_cost(self.user_store, self.save_users, self.config)
        queue_prompt = "You maintain a simple queue for viewer battles. Whenever you are asked, you will either add somebody to the queue, advance the queue, or display the queue. When asked to add somebody to the queue (or if someone leaves their message body empty and just puts the !queue command into chat), add that person to the next available position in the queue and display the whole queue in your response. When asked to advance the queue, remove the person at the top and send the new queue in your response. Sometimes people will request to be added simply by using your command and not including a message in the body, in these cases please add them to the queue. When asked to display the queue, send the entire queue without making any changes to it. You should send the entire queue every response no matter what. When displaying the queue, always remember not to leave anyone out. Make sure the whole entire queue is displayed and make sure that you do not forget anybody. To cut down on duplicate actions, if people try to remove people, add people, or advance the queue quickly in succession (less than one minute apart) only do it once. If the message portion of a user's input is left out, just add them to the queue. This happens because people just put '!queue' into the chat. Only allow users to be in the queue once at a time. "
        message_content = f"Username and username info: '{username}'. Message: {message}"
        combined_context = await process_queue_input(message_content, self.memory, self.chatbot)
        bot_response = await get_bot_response(message_content, f"{queue_prompt} {combined_context}", self.chatbot)
        await process_queue_output(bot_response, channel, combined_context, self.chatbot, self.memory)

    async def handle_background_command(self, username, message, channel: Channel):
        channel = ""
        await raise_cost(self.user_store, self.save_users, self.config)
        message_content = f"Username and username info: '{username}'. Message: {message}"
        background_prompt = "You help maintain the background image for a stream via your word dictations. Please create a vivid description in under 490 characters for the attached user's request for a background. Your response should contain nothing but the background prompt. UNDER NO CIRCUMSTANCES SHOULD YOUR RESPONSE EXCEED 490 CHARACTERS"
        combined_context = await process_input(message_content, channel, self.memory, self.chatbot, self.config)
        background_prompt = await get_bot_response(f"{background_prompt} {message_content}", combined_context, self.chatbot)
        truncated_bg = truncate_text(background_prompt, 490)
        await channel.send(f"[{self.config.name}]: Updating background to '{truncated_bg}.")
        print(f"background: {background_prompt}")
        background = await get_background(background_prompt, self.config, self.chatbot)
        display_file(background, self.config.name, 'background')