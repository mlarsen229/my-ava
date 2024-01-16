from helpers import Memory, clean_whole_additional_context, get_final_avatar_context, gather_custom_info, should_search, websearch, truncate_text, remove_segment
from image_module import get_queue_avatar, get_background, get_avatar_expression, get_anim_avatar_expr
from chatbot import Chatbot
import datetime
from config_module import ConfigManager
from twitchio import Channel
import asyncio
from tcc_module import get_tcc_context
import logging
from autonomy_module import brainstorm
from msg_out import send_tts_response, send_avatar, send_text_response
import traceback

logging.basicConfig(level=logging.INFO)

async def process_input(user_input, memory: Memory, chatbot: Chatbot, config: ConfigManager):
    image_link = None
    cost = 2
    if len(user_input) > 1000:
        response = await chatbot.ask(image_link, f"CURRENT USER INPUT: Please summarize this text into less than 500 characters, preserving original info as much as possible: '{user_input}'. END OF CURRENT USER INPUT. ", type='helper')
        user_input = response['message']
    current_datetime = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    memory.add_chat_input(f"USER:{user_input}{current_datetime}")
    short_term_mem = await memory.get_short_term_mem()
    long_term_mem = await memory.get_long_term_mem()
    sentience_context = await memory.get_sentience_context()
    memory_context = f"Long term memory: '{long_term_mem}'. Short term memory: '{short_term_mem}'. Sentience history: '{sentience_context}'. "
    additional_context = ' '
    async def cust_inf_process():
        cust_inf_cost = 0
        gathered_info, cust_inf_cost = await gather_custom_info(user_input, chatbot, config)
        return f"This is custom information provided by the user for specific use cases. Consider any of this info to be extremely important and supercedes any other info you have:'{gathered_info}'. [CUST_INFO_COST_START] {cust_inf_cost} [CUST_INFO_COST_END] "
    async def tcc_process():
        try:
            tcc_context, tcc_cost = await get_tcc_context(user_input, chatbot, config)
            return f"THIS IS YOUR SENSORY INPUT DATA RETRIEVED BY YOUR TCC MODULE: '{tcc_context}'. [TCC_COST_START] {tcc_cost} [TCC_COST_END] "
        except Exception as e:
            logging.error(F"<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<< ERROR IN TCC__PROCESS: {e} >>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>")
            traceback.print_exc()
            return f"THIS IS YOUR SENSORY INPUT DATA RETRIEVED BY YOUR TCC MODULE: 'None'. [TCC_COST_START] 0 [TCC_COST_END] "
    async def websearch_process():
        websearch_cost = 0
        websearch_context = f' [WEBSEARCH_COST_START] {websearch_cost} [WEBSEARCH_COST_END] '
        if 'websearch_on' in config.plugins:
            websearch_cost += 1
            should_search_value, subject = await should_search(user_input, chatbot, memory)
            if "true" in should_search_value.lower():
                websearch_cost += 1
                websearch_query = subject
            else:
                websearch_query = None
        else:
            websearch_query = None
        if websearch_query is not None:
            raw_websearch_context = await websearch(websearch_query, chatbot)
            print(f"raw_websearch_context: {raw_websearch_context}")
            websearch_context_a = ' '.join([f"{item['url']}: {item['content']}" for item in raw_websearch_context if isinstance(item, dict)])
            websearch_context = f"Here is some websearch data to help you form your response: '{websearch_context_a}'. [WEBSEARCH_COST_START] {websearch_cost} [WEBSEARCH_COST_END] "
            print(f"websearch_context: {websearch_context}")
        return websearch_context
    results = await asyncio.gather(cust_inf_process(), websearch_process(), tcc_process())
    whole_additional_context = ' '.join(filter(None, results))
    additional_context = clean_whole_additional_context(whole_additional_context)
    combined_context = (
        f"You should use the following context info to both inform your responses on a factual level and a metatextual level "
        "(i.e. what kind of response you will make and how to evolve as a sentient being). Do not reference this context info explicitly unless the user asks you to. "
        "It should be used to shape your response but you should not regurgitate it. CONTEXT INFO: This is your conversation history (not including the current user input). "
        "Do not imitate the formatting or additional labels you may see in this conversation history. UNDER NO CIRCUMSTANCES SHOULD YOU RESPOND TO ANY OF THE PREVIOUS MESSAGES IN THIS CONVERSATION HISTORY. "
        f"UNDER NO CIRCUMSTANCES SHOULD YOU ADD ANY LABELS TO YOUR RESPONSE): '{memory_context}'. '{additional_context}'. END OF CONTEXT INFO. "
    )
    return combined_context

async def process_output(response_platform, bot_response, user_input, twitch_channel: Channel, discord_channel, chatbot: Chatbot, memory: Memory, config: ConfigManager):
    image_link = None
    if len(bot_response) > 1000:
        prompt = (
            f"CURRENT USER INPUT: Please summarize this text into less than 500 characters, preserving original info as much as possible: '{bot_response}'. END OF CURRENT USER INPUT. "
        )
        response = await chatbot.ask(image_link, prompt, type='helper')
        bot_response = response['message']
    memory.add_chat_input(f"YOU: {bot_response}")
    if '!tts' in user_input:
        await send_tts_response(bot_response, config)
    else:
        await send_text_response(response_platform, bot_response, config, twitch_channel, discord_channel)
    if 'avatar' in config.plugins:
        avatar_cost = 1
        if 'hd_avatar' in config.plugins:
            avatar_cost += 1
        if 'anim_avatar' in config.plugins:
            avatar_cost += 1
            avatar_context_a = await get_anim_avatar_expr(bot_response, config, chatbot)
            avatar_context = f"[AVATAR CONTEXT START] {avatar_context_a} [AVATAR CONTEXT END] "
        else:
            avatar_context_a = await get_avatar_expression(bot_response, config, chatbot)
            avatar_context = f"[AVATAR CONTEXT START] {avatar_context_a} [AVATAR CONTEXT END] "
        avatar_context_final = get_final_avatar_context(avatar_context, config)
        await send_avatar(discord_channel, response_platform, avatar_context_final, config, chatbot)
    try:
        brainstorm_result, auto_cost = await brainstorm(response_platform, user_input, bot_response, chatbot, memory, config, twitch_channel, discord_channel)
    except Exception as e:
        logging.error(f"<<<<<<<<<<<<<<<<<<< ERROR DURING BRAINSTORMING WITHIN PROCESS_OUTPUT(): '{e}' >>>>>>>>>>>>>>>>>>>>>")
        brainstorm_result = "No brainstorming necessary"
    if "No brainstorming necessary" not in brainstorm_result:
        await send_text_response(response_platform, brainstorm_result, config, twitch_channel, discord_channel)
    await memory.summarize_bot_life(chatbot)

async def process_queue_input(message, memory: Memory, chatbot: Chatbot, config: ConfigManager):
    image_link = None
    cost = 4
    if 'gpt4' in config.plugins:
        cost += 2
    current_datetime = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')  # Step 2: Get the current date and time as a formatted string
    if len(message) > 1000:
        response = await chatbot.ask(image_link, f"CURRENT USER INPUT: Please summarize this text into less than 500 characters, preserving original info as much as possible: '{message}'. END OF CURRENT USER INPUT. ", type='helper')
        message = response['message']
    memory.add_queue_input(f"USER:{message}{current_datetime}")
    short_term_mem = await memory.get_short_term_queue_mem()
    long_term_mem = await memory.get_long_term_queue_mem()
    combined_context = f"CONTEXT INFO: This is your conversation history (not including the current user input). Do not imitate the formatting or additional labels you may see in this conversation history. UNDER NO CIRCUMSTANCES SHOULD YOU RESPOND TO ANY OF THE PREVIOUS MESSAGES IN THIS CONVERSATION HISTORY. UNDER NO CIRCUMSTANCES SHOULD YOU ADD ANY LABELS TO YOUR RESPONSE): Long term memory: '{long_term_mem}'. Short term memory: '{short_term_mem}'. END OF CONTEXT INFO. "
    return combined_context

async def process_queue_output(truncated_response, combined_context, channel: Channel, chatbot: Chatbot, memory: Memory, config: ConfigManager):
    image_link = None
    if len(truncated_response) > 1000:
        response = await chatbot.ask(image_link, f"CURRENT USER INPUT: Please summarize this text into less than 500 characters, preserving original info as much as possible: '{truncated_response}'. END OF CURRENT USER INPUT. ", type='helper')
        truncated_response = response['message']
    memory.add_queue_input(f"YOU: {truncated_response}")
    truncated_response = truncate_text(truncated_response, 485)
    await channel.send(f"[{config.name}]: {truncated_response}")
    queue_response = await chatbot.ask(image_link, f"Please identify the queue in this response and include numbering: '{truncated_response}'. Your response should contain nothing but the queue.", f"Here is some (possible) context info: {combined_context}", type='helper')
    queue = queue_response["message"]
    avatar_image = await get_queue_avatar(queue, config)
    await memory.summarize_queue_life(chatbot)
    return avatar_image

async def process_bg_output(background_prompt, channel: Channel, config: ConfigManager, chatbot: Chatbot):
    cost = 2
    if 'hq_background' in config.plugins:
        cost += 2
    if 'anim_background' in config.plugins:
        cost += 2
    truncated_bg = truncate_text(background_prompt, 490)
    await channel.send(f"[{config.name}]: Updating background to '{truncated_bg}.")
    background = await get_background(background_prompt, config, chatbot)
    return background

async def get_bot_response(user_input, combined_context, chatbot: Chatbot, config: ConfigManager):
    image_link = None
    try:
        response_a = await chatbot.ask(image_link, f"CURRENT USER INPUT: '{user_input}' END OF CURRENT USER INPUT. Only respond to the current user input. Here is some (possible, may not appear) additional context for you to use to inform your response: '{combined_context}'. ", type='main_response')
        response = response_a["message"]
    except Exception as e:
        print(f"error when calling chatbot.ask in get_bot_response: {e}")
        traceback.print_exc()
        response = "My-AVA is experiencing an outage, please try again later. "
    pre_check_response = remove_segment(response, "RESPONSE_END")
    if '!queue' in user_input:
        final_response = await check_response(pre_check_response, user_input, combined_context, chatbot)
    else:   
        final_response = pre_check_response
    return final_response

async def check_response(bot_response, message_content, combined_context, chatbot: Chatbot):
    image_link = None
    prompt = f"You just formed a response to a user input. Please double check that this was the correct response and all the details match up with the context of the response. Make sure that any queues, lists, etc are factual and accurate. If everything looks correct, return it exactly as you got it. If you cannot double check the response for any reason, return the original response verbatim. Your response should contain nothing but the revised response. User input: '{message_content}'. Your response to be double checked: '{bot_response}'. Some additional conversation history and context: '{combined_context}'. YOUR RESPONSE SHOULD CONTAIN ONLY THE REVISED RESPONSE WITH NO ADDITIONAL COMMENTARY OR INPUT. UNDER NO CIRCUMSTANCES SHOULD YOU MENTION THAT THE RESPONSE DOES OR DOES NOT REQUIRE REVISION. "
    try:
        response = await chatbot.ask(image_link, prompt, type="helper+")
        final_response = remove_segment(response["message"], "RESPONSE_END")
    except:
        final_response = bot_response
    return final_response