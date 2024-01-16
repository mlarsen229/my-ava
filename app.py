import os
from chatbot import Chatbot
from helpers import Memory, load_memory, truncate_text
from config_module import ConfigManager, dict_to_config, config_to_dict, config_store
import logging
from threading import Lock
from create_bot import create_bot
import traceback
    
bot_lock = Lock()

logging.basicConfig(level=logging.INFO)

active_bots = {}

async def activate_bot(name, raw_config):
    with bot_lock:
        config = dict_to_config(raw_config) if isinstance(raw_config, dict) else raw_config
        if name in active_bots:
            return False
        try:
            chatbot = Chatbot(config)
            memory = Memory(config)
            loaded_memory = load_memory(memory)
            bots, loops = create_bot(config, chatbot, loaded_memory)
            active_bots[name] = {"bots": bots, "loops": loops}
            for bot in bots:
                try:
                    await bot.start()
                except Exception as e:
                    print(f"error in run bot: {e}")
            return True
        except Exception as e:
            logging.error(f"Exception caught in activate_bot: {e}")
            traceback.print_exc()
            return False

async def create_config():
    print("Create your own Autonomous Virtual Agent:")
    avatar_seed = 1
    bgcost = 0
    queuecost = 0
    user = input('User name: ')
    name = input('AVA name: ')
    avatar = input('Avatar description: ')
    base_prompt = input('Base prompt: ')
    if len(base_prompt) > 1000:
        truncate_text(base_prompt, 1000)
    voice = input('Voice(google tts code): ')
    bot_type = input('Platform(twitch, discord, standard): ')
    plugins = input('Plugins(gpt4, autonomy, websearch, sentience, queue, avatar, background): ')
    if 'avatar' in plugins:
        avatar_plugins = input('Avatar plugins(hq_avatar, anim_avatar): ')
        plugins += avatar_plugins
        if 'anim_avatar' in plugins:
            avatar_seed = input('Avatar seed: ')
    if bot_type == 'twitch':
        channel = input('Twitch channel: ')
        chat_command_bits = input('Twitch chat command bits: ')
        tts_command_bits = input('Twitch tts command bits: ')
        if 'queue' in plugins:
            queuecost = input('Twitch queue command bits: ')
        else:
            queuecost = 0
        if 'bg' in plugins:
            bgcost = input('Twitch background command bits: ')
            bg_plugins = input('Background plugins(hq_background, anim_background): ')
            plugins += bg_plugins
        else:
            bgcost = 0
    elif bot_type == 'discord':
        chat_command_bits = 0
        tts_command_bits = 0
        queuecost = 0
    elif bot_type == 'standard':
        channel = None
        chat_command_bits = 0
        tts_command_bits = 0
        queuecost = 0
    custom_info = input('Custom info: ')
    custom_files = input('Custom file paths: ')
    chat_reward_id = None
    tts_reward_id = None
    queue_reward_id = None
    background_reward_id = None
    new_config = ConfigManager(channel, name, avatar, avatar_seed, base_prompt, custom_info, custom_files, voice, chat_command_bits, tts_command_bits, user, bot_type, chat_reward_id, tts_reward_id, queue_reward_id, background_reward_id, plugins, queuecost, bgcost)
    serialized_config = config_to_dict(new_config)
    config_store[name] = serialized_config
    if await activate_bot(name, new_config):
        return "Configuration created and bot activated"
    else:
        return "Internal Server Error"