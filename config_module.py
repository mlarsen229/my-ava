config_store = {}

class ConfigManager:
    def __init__(self, channel=None, name=None, avatar=None, base_prompt=None, voice=None, chat_command_bits=None, tts_command_bits=None, user=None, bot_type=None, chat_reward_id=None, tts_reward_id=None, queue_reward_id=None, background_reward_id=None, plugins=None, cost=None, queuecost=None):
        self.channel = channel
        self.name = name
        self.avatar = avatar
        self.base_prompt = base_prompt
        self.voice = voice
        self.chat_command_bits = chat_command_bits
        self.tts_command_bits = tts_command_bits
        self.user = user
        self.bot_type = bot_type
        self.chat_reward_id = chat_reward_id
        self.tts_reward_id = tts_reward_id
        self.queue_reward_id = queue_reward_id
        self.background_reward_id = background_reward_id
        self.plugins = plugins
        self.cost = cost
        self.queuecost = queuecost

def config_to_dict(config):
    return {
        'channel': config.channel,
        'name': config.name,
        'avatar': config.avatar,
        'base_prompt': config.base_prompt,
        'voice': config.voice,
        'chat_command_bits': config.chat_command_bits,
        'tts_command_bits': config.tts_command_bits,
        'user': config.user,
        'bot_type': config.bot_type,
        'chat_reward_id': config.chat_reward_id,
        'tts_reward_id': config.tts_reward_id,
        'queue_reward_id': config.queue_reward_id,
        'background_reward_id': config.background_reward_id,
        'plugins': config.plugins,
        'cost': config.cost,
        'queuecost': config.queuecost
    }

def dict_to_config(config_dict):
    return ConfigManager(**config_dict)

def save_configs(config_store):
    #insert logic for saving bot configs
    pass