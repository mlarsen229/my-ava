import asyncio
from chatbot import Chatbot
from helpers import Memory, truncate_text
from config_module import ConfigManager, dict_to_config, config_to_dict, config_store
import logging
import json
from threading import Thread
from threading import Lock
from bot_module import create_bot
import traceback

bot_lock = Lock()

active_bots = {}

async def activate_bot(name, raw_config):
    with bot_lock:
        # Convert raw_config to ConfigManager object if it's a dictionary
        config = dict_to_config(raw_config) if isinstance(raw_config, dict) else raw_config
        if name in active_bots:
            return False
        try:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            chatbot = Chatbot(config)  # Pass ConfigManager object
            memory = Memory(config)
            bot = create_bot(loop, config, chatbot, memory)
            active_bots[name] = {"bot": bot, "loop": loop}
            await bot.start()
            print(f"Bot activated: {name}")
            return True
        except Exception as e:
            logging.error(f"Exception caught in activate_bot: {e}")
            return False
    
async def create_config():
    print("Create your own Autonomous Virtual Avatar:")
    #this is for programmatic bot creation
    #you can manually fill this info in and call create_config in main.py, or implement your own bot creation frontend
    try:
        user = input('User name: ')
        name = input('AVA name: ')
        avatar = input('Avatar description: ')
        base_prompt = input('Base prompt: ')
        if len(base_prompt) > 1000:
            truncate_text(base_prompt, 1000)
        voice = input('Voice(google tts code): ')
        bot_type = input('Platform(twitch, discord, or standard): ')
        plugins = input('Plugins(gpt4, dall-e-3, websearch, sentience, queue, avatar, background): ')
        if bot_type == 'twitch':
            channel = input('Twitch channel: ')
            chat_command_bits = input('Twitch chat command bits: ')
            tts_command_bits = input('Twitch tts command bits: ')
            if 'queue' in plugins:
                queuecost = input('Twitch queue command bits: ')
            else:
                queuecost = 0
        elif bot_type == 'discord':
            channel = input('Discord channel: ')
            chat_command_bits = 0
            tts_command_bits = 0
            queuecost = 0
        elif bot_type == 'standard':
            channel = None
            chat_command_bits = 0
            tts_command_bits = 0
            queuecost = 0
        chat_reward_id = None
        tts_reward_id = None
        queue_reward_id = None
        background_reward_id = None
        cost = 2
        if "gpt4" in plugins:
            cost += 1
        if "dall-e-3" in plugins:
            cost += 2
        if "websearch" in plugins:
            cost += 1
        if "sentience" in plugins:
            cost += 1
        if "queue" in plugins:
            cost += 1
        if "avatar" in plugins:
            cost += 1
        new_config = ConfigManager(channel, name, avatar, base_prompt, voice, chat_command_bits, tts_command_bits, user, bot_type, chat_reward_id, tts_reward_id, queue_reward_id, background_reward_id, plugins, cost, queuecost)
        serialized_config = config_to_dict(new_config)
        config_store[name] = serialized_config
        if await activate_bot(name, new_config):
            return
        else:
            return
    except Exception as e:
        print(f"Exception in create_config: '{e}'.")
        traceback.print_exc()
        return