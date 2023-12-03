import asyncio
from chatbot import Chatbot
from helpers import Memory, load_memory
from config_module import dict_to_config, config_store, save_json_locally
import logging
import json
from threading import Thread
from google.cloud import storage
from google.cloud.exceptions import NotFound
from threading import Lock
from bot_module import create_bot
import traceback

GOOGLE_APPLICATION_CREDENTIALS = ""

bot_lock = Lock()

active_bots = {}
user_store = {}

def save_users():
    #your own user store logic
    pass

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
            bot = create_bot(loop, config, chatbot, loaded_memory, user_store, save_users)
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

#Replace config_store.json loading logic to use local configs if desired
def load_configs():
    try:
        storage_client = storage.Client.from_service_account_json(GOOGLE_APPLICATION_CREDENTIALS)
        bucket = storage_client.get_bucket('yourbucket')
        blob = bucket.blob('config_store.json')
        config_data = json.loads(blob.download_as_text())
        #print(f"config store during load_configs: {config_data}")
        save_json_locally(config_data, "config_store.json")
        for name, config in config_data.items():
            config_store[name] = config
            config_obj = dict_to_config(config)  # Convert to ConfigManager object
            activate_bot(name, config_obj)
        return None
    except NotFound as gce:
        logging.error(f"Google Cloud Error during load_configs: {gce}")
    except json.JSONDecodeError as jde:
        logging.error(f"JSON Decode Error during load_configs: {jde}")
    except Exception as e:
        logging.error(f"General Exception during load_configs: {e}")
        traceback.print_exc()