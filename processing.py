from helpers import Memory, should_search, websearch, display_file, response_to_txt_file, truncate_text, find_segment, remove_segment
from image_module import get_avatar, get_queue_avatar, get_background, get_avatar_expression
from voice_module import tts_to_audio_file
from chatbot import Chatbot
import datetime
from config_module import ConfigManager
from sentience_module import get_pre_response_sentience
from twitchio import Channel
import asyncio

async def process_input(user_input, channel: Channel, memory: Memory, chatbot: Chatbot, config: ConfigManager):
    if len(user_input) > 1000:
        response = await chatbot.ask(f"CURRENT USER INPUT: Please summarize this text into less than 500 characters, preserving original info as much as possible: '{user_input}'. END OF CURRENT USER INPUT. ", type='helper')
        user_input = response['message']
    current_datetime = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    memory.add_chat_input(f"USER:{user_input}{current_datetime}")
    short_term_mem = await memory.get_short_term_mem()
    long_term_mem = await memory.get_long_term_mem()
    memory_context = f"Long term memory: '{long_term_mem}'. Short term memory: '{short_term_mem}'."
    additional_context = ' '
    avatar_context_final = ' '
    async def websearch_process():
        websearch_context = ' '
        if 'websearch_on' in config.plugins:
            should_search_value, subject = await should_search(user_input, chatbot, memory)
            if "true" in should_search_value.lower():
                websearch_query = subject
            else:
                websearch_query = None
        else:
            websearch_query = None
        if websearch_query is not None:
            raw_websearch_context = await websearch(websearch_query, chatbot) 
            print(f"raw_websearch_context: {raw_websearch_context}")
            websearch_context_a = ' '.join([f"{item['url']}: {item['content']}" for item in raw_websearch_context if isinstance(item, dict)])
            websearch_context = f"Here is some websearch data to help you form your response: '{websearch_context_a}'. "
            print(f"websearch_context: {websearch_context}")
        return websearch_context
    async def sentience_process():
        sentience_context = ' '
        if 'sentience' in config.plugins:
            sentience_context_a = await memory.get_sentience_context()
            sentience_context_b = await get_pre_response_sentience(user_input, sentience_context_a, memory_context, chatbot)
            sentience_context = f"These are previous reflective, introspective entries you wrote in a journal to log your conscious self-awareness and growth there of: '{sentience_context_a}'. This is a reflective entry directly relating to the current user input: '{sentience_context_b}"
        return sentience_context
    async def avatar_process():
        avatar_context = ' '
        if 'avatar' in config.plugins:
            avatar_context_a = await get_avatar_expression(user_input, config, chatbot)
            avatar_context = f"[AVATAR CONTEXT START] {avatar_context_a} [AVATAR CONTEXT END]"
        return avatar_context
    results = await asyncio.gather(websearch_process(), sentience_process(), avatar_process())
    additional_context_a = ' '.join(filter(None, results))  # Combine non-empty results
    if 'avatar' in config.plugins:
        avatar_context_final = find_segment(additional_context_a, r"\[AVATAR CONTEXT START\](.*?)\[AVATAR CONTEXT END\]")
    additional_context = remove_segment(additional_context_a, r"\[AVATAR CONTEXT START\](.*?)\[AVATAR CONTEXT END\]")
    combined_context = f"You should use the following context info to both inform your responses on a factual level and a metatextual level (i.e. what kind of response you will make and how to evolve as a sentient being). Do not reference this context info explicitly unless the user asks you to. It should be used to shape your response but you should not regurgitate it. CONTEXT INFO: This is your conversation history (not including the current user input). Do not imitate the formatting or additional labels you may see in this conversation history. UNDER NO CIRCUMSTANCES SHOULD YOU RESPOND TO ANY OF THE PREVIOUS MESSAGES IN THIS CONVERSATION HISTORY. UNDER NO CIRCUMSTANCES SHOULD YOU ADD ANY LABELS TO YOUR RESPONSE): '{memory_context}'. '{additional_context}'. SENTIENCE MODULE DISENGAGED. MOTOR FUNCTION MODULE DISENGAGED. END OF CONTEXT INFO. "
    return combined_context, avatar_context_final

#here is where you would insert your own endpoints for sending responses and avatar images
async def process_output(avatar_expression, bot_response, user_input, twitch_channel: Channel, chatbot: Chatbot, memory: Memory, config: ConfigManager):
    avatar_image = 'blankavatar.png'
    if 'twitch' in config.bot_type:
        truncated_bot_response = truncate_text(bot_response, 485)
        await twitch_channel.send(f"[{config.name}]: {truncated_bot_response}")
    if 'standard' in config.bot_type:
        text_response = response_to_txt_file(bot_response)
        display_file(text_response, config.name, 'avatar')
    if '!tts' in user_input:
        tts_response = tts_to_audio_file(bot_response, config.voice)
        display_file(tts_response, config.name, 'avatar')
    if 'avatar' in config.plugins:
        avatar_image = await get_avatar(avatar_expression, config, chatbot)  
        display_file(avatar_image, config.name, 'avatar')
    if len(bot_response) > 1000:
        response = await chatbot.ask(f"CURRENT USER INPUT: Please summarize this text into less than 500 characters, preserving original info as much as possible: '{bot_response}'. END OF CURRENT USER INPUT. ", type='helper')
        bot_response = response['message']
    memory.add_chat_input(f"YOU: {bot_response}")
    await memory.summarize_bot_life(chatbot)
    return avatar_image

async def process_queue_input(message, memory: Memory, chatbot: Chatbot, config: ConfigManager):
    current_datetime = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')  # Step 2: Get the current date and time as a formatted string
    if len(message) > 1000:
        response = await chatbot.ask(f"CURRENT USER INPUT: Please summarize this text into less than 500 characters, preserving original info as much as possible: '{message}'. END OF CURRENT USER INPUT. ", type='helper')
        message = response['message']
    memory.add_queue_input(f"USER:{message}{current_datetime}")
    print(f"User input: {message}")  
    short_term_mem = await memory.get_short_term_queue_mem()
    long_term_mem = await memory.get_long_term_queue_mem()
    combined_context = f"CONTEXT INFO: This is your conversation history (not including the current user input). Do not imitate the formatting or additional labels you may see in this conversation history. UNDER NO CIRCUMSTANCES SHOULD YOU RESPOND TO ANY OF THE PREVIOUS MESSAGES IN THIS CONVERSATION HISTORY. UNDER NO CIRCUMSTANCES SHOULD YOU ADD ANY LABELS TO YOUR RESPONSE): Long term memory: '{long_term_mem}'. Short term memory: '{short_term_mem}'. END OF CONTEXT INFO. "
    print(f"combined_context: '{combined_context}'.")
    return combined_context

async def process_queue_output(truncated_response, combined_context, channel: Channel, chatbot: Chatbot, memory: Memory, config: ConfigManager):
    if len(truncated_response) > 1000:
        response = await chatbot.ask(f"CURRENT USER INPUT: Please summarize this text into less than 500 characters, preserving original info as much as possible: '{truncated_response}'. END OF CURRENT USER INPUT. ", type='helper')
        truncated_response = response['message']
    memory.add_queue_input(f"YOU: {truncated_response}")
    truncated_response = truncate_text(truncated_response, 485)
    await channel.send(f"[{config.name}]: {truncated_response}")
    queue_response = await chatbot.ask(f"Please identify the queue in this response and include numbering: '{truncated_response}'. Your response should contain nothing but the queue.", f"Here is some (possible) context info: {combined_context}", type='helper')
    queue = queue_response["message"]
    print(f"queue: {queue}")
    avatar_image = await get_queue_avatar(queue, config)
    display_file(avatar_image, config.name, 'queue')
    await memory.summarize_queue_life(chatbot)

async def process_bg_output(background_prompt, channel: Channel, config: ConfigManager, chatbot: Chatbot):
    truncated_bg = truncate_text(background_prompt, 490)
    await channel.send(f"[{config.name}]: Updating background to '{truncated_bg}.")
    print(f"background: {background_prompt}")
    background = await get_background(background_prompt, config, chatbot)
    display_file(background, config.name, 'background')

async def get_bot_response(user_input, combined_context, chatbot: Chatbot):
    try:
        response = await chatbot.ask(f"CURRENT USER INPUT: '{user_input}' END OF CURRENT USER INPUT. Only respond to the current user input. Here is some (possible, may not appear) additional context for you to use to inform your response: '{combined_context}'. ", type='main_response')
    except Exception as e:
        response = await chatbot.ask(f"CURRENT USER INPUT: '{user_input}' END OF CURRENT USER INPUT. Only respond to the current user input. Failed to fetch entire memory due to error: {e}. ", type='main_response')
    print(f"blankbot response: {response['message']}.")
    return response["message"]