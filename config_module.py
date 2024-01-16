config_store = {}

class ConfigManager:
    def __init__(self, channel=None, name=None, avatar=None, avatar_seed=1, base_prompt=None, custom_info=" ", custom_files=" ", voice=None, chat_command_bits=None, tts_command_bits=None, user=None, bot_type=None, chat_reward_id=None, tts_reward_id=None, queue_reward_id=None, background_reward_id=None, plugins=None, queuecost=None, bgcost=None):
        self.channel = channel
        self.name = name
        self.avatar = avatar
        self.avatar_seed = avatar_seed
        self.base_prompt = base_prompt
        self.custom_info = custom_info
        self.custom_files = custom_files
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
        self.queuecost = queuecost
        self.bgcost = bgcost

def config_to_dict(config):
    return {
        'channel': config.channel,
        'name': config.name,
        'avatar': config.avatar,
        'avatar_seed': config.avatar_seed,
        'base_prompt': config.base_prompt,
        'custom_info': config.custom_info,
        'custom_files': config.custom_files,
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
        'queuecost': config.queuecost,
        'bgcost': config.bgcost
    }

def dict_to_config(config_dict):
    return ConfigManager(**config_dict)