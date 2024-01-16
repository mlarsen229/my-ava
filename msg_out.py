import logging
from config_module import ConfigManager
from helpers import truncate_text, response_to_txt_file
from voice_module import tts_to_audio_file
from chatbot import Chatbot
from image_module import get_avatar
from twitchio import Channel
import discord
import traceback
import uuid

logging.basicConfig(level=logging.INFO)

async def send_text_response(response_platform, bot_response, config: ConfigManager, twitch_channel: Channel, discord_channel):
    if "discord" in response_platform:
        await discord_channel.send(f"[{config.name}]: {bot_response}")
    if 'twitch' in response_platform:
        truncated_bot_response = truncate_text(bot_response, 485)
        await twitch_channel.send(f"[{config.name}]: {truncated_bot_response}")
    if 'standard' in response_platform:
        print(f"[{config.name}]: {bot_response}")
        text_response = response_to_txt_file(bot_response)
    pass

async def send_tts_response(bot_response, config: ConfigManager):
    tts_response = tts_to_audio_file(bot_response, config.voice)
    pass
    
async def send_avatar(discord_channel, response_platform, avatar_expression, config: ConfigManager, chatbot: Chatbot):
    try:
        avatar_image = await get_avatar(avatar_expression, config, chatbot)
        if "discord" in response_platform:
            avatar_image_path = f"{config.name}_avatar_{uuid.uuid4()}.png"
            avatar_image.save(avatar_image_path)
            await discord_channel.send(file=discord.File(avatar_image_path))
            return
    except Exception as e:
        print(f"error in send_avatar during process_output: {e}")
        traceback.print_exc()