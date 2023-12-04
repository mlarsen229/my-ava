import asyncio
from chatbot import Chatbot
from helpers import Memory, truncate_text, load_memory
from config_module import ConfigManager, save_configs, dict_to_config, config_to_dict, config_store
import logging
import json
from threading import Thread
from threading import Lock
from bot_module import create_bot
import traceback

bot_lock = Lock()

active_bots = {}
user_store = {}

def activate_bot(name, raw_config):
    with bot_lock:
        # Convert raw_config to ConfigManager object if it's a dictionary
        config = dict_to_config(raw_config) if isinstance(raw_config, dict) else raw_config
        print(f"config during activate_bot: {config}")
        if name in active_bots:
            return False
        try:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            chatbot = Chatbot(config)  # Pass ConfigManager object
            memory = Memory(config)
            loaded_memory = load_memory(memory)
            bot = create_bot(loop, config, chatbot, loaded_memory)
            active_bots[name] = {"bot": bot, "loop": loop}

            def run_bot():
                try:
                    loop.run_until_complete(bot.start())
                finally:
                    loop.close()
            try:
                Thread(target=run_bot).start()
            except Exception as e:
                print(f"error in run bot: {e}")
            print(f"Bot activated: {name}")
            return True
        except Exception as e:
            logging.error(f"Exception caught in activate_bot: {e}")
            return False

def load_configs():
    #this is for loading bots, easy to call in main.py with config data filled in below
    try:
        config_data = 'your config data (see config_module for format specs)'
        for name, config in config_data.items():
            config_store[name] = config
            config_obj = dict_to_config(config)  # Convert to ConfigManager object
            activate_bot(name, config_obj)
        return None
    except Exception as e:
        logging.error(f"General Exception during load_configs: {e}")
        traceback.print_exc()
    
def create_config():
    #this is for programmatic bot creation
    #you can manually fill this info in and call create_config in main.py, or implement your own bot creation frontend
    try:
        channel = 'channel'
        name = 'name'
        avatar = 'avatar'
        base_prompt = 'base_prompt'
        if len(base_prompt) > 1000:
            truncate_text(base_prompt, 1000)
        #voice code for google tts
        voice = 'voice'
        chat_command_bits = 'chat_command_bits'
        tts_command_bits = 'tts_command_bits'
        bot_type = 'bot_type'
        chat_reward_id = None
        tts_reward_id = None
        queue_reward_id = None
        background_reward_id = None
        plugins = 'plugins'
        user = 'user'
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
        queuecost = 'queuecost'
        new_config = ConfigManager(channel, name, avatar, base_prompt, voice, chat_command_bits, tts_command_bits, user, bot_type, chat_reward_id, tts_reward_id, queue_reward_id, background_reward_id, plugins, cost, queuecost)
        serialized_config = config_to_dict(new_config)
        #print(f"Serialized config: {serialized_config}")
        config_store[name] = serialized_config
        #print(f"Config store before save: {config_store}")
        save_configs(config_store)
        #print(f"Config store after save: {config_store}")
        print(f"Contents of config_store.json: {json.dumps(config_store, indent=4)}")
        if activate_bot(name, new_config):
            return
        else:
            return
    except Exception as e:
        print(f"Exception in create_config: '{e}'.")
        traceback.print_exc()
        return