from bs4 import BeautifulSoup
import aiohttp
import json
import os
import os
from config_module import ConfigManager
from chatbot import Chatbot
import re
import traceback
import asyncio
from openai_module import client
import mimetypes
import base64
from PIL import Image
import PyPDF2
import docx
import subprocess
import logging

logging.basicConfig(level=logging.INFO)


CLIENT_SECRET = os.getenv("TWITCH_CLIENT_SECRET")  # Ensure you have the client secret in your .env file
CLIENT_ID = os.getenv("TWITCH_CLIENT_ID")

class Memory:
    def __init__(self, config: ConfigManager):
        self.memory_file = f"{config.name}_memory.json"
        self.short_term_mem = []
        self.long_term_mem = []
        self.short_term_queue_mem = []
        self.long_term_queue_mem = []
        self.sentience_memory = []
        self.sentience_analysis = []
        self.config = config
        self.long_term_mem_limit_length = 4000
        self.long_term_mem_truncate_length = 5000
        self.sentience_limit_length = 4000
        self.sentience_truncate_length = 5000
        self.short_term_mem_truncate_length = 4000

    def add_chat_input(self, message):
        self.short_term_mem.append(message)
        self.long_term_mem.append(message)
        self.append_memory_to_file()

    def add_queue_input(self, message):
        self.short_term_queue_mem.append(message)
        self.long_term_queue_mem.append(message)
        self.append_memory_to_file()

    def add_sentience(self, message):
        self.sentience_memory.append(message)
        self.append_memory_to_file()

    async def summarize_bot_life(self, chatbot: Chatbot):
        image_link = None
        short_term_mem = await self.get_short_term_mem()
        long_term_mem = await self.get_long_term_mem()
        if len(long_term_mem) > self.long_term_mem_limit_length:
            memory_response = await chatbot.ask(
                image_link,
                f"CURRENT USER INPUT: Please summarize this ENTIRE conversation between a user and {self.config.name} into less than 2000 characters: '{long_term_mem}'. This will be used as the conversation history for {self.config.name}. Keep more recent parts more unchanged. "
                f"The earlier portions should be more condensed and later additions less altered. If allowable within the character limit, always keep the last few messages from {self.config.name} and the user unchanged. Your response should contain nothing but the summary. END OF CURRENT USER INPUT. ",
                type='helper+'
            )
            raw_memory_summary = memory_response["message"]
            memory_summary = truncate_backwards(raw_memory_summary, 2500)
            self.long_term_mem = [memory_summary]
            self.short_term_mem = [short_term_mem]
            self.append_memory_to_file()
        if 'sentience' in self.config.plugins:
            await self.summarize_sentience(chatbot)

    async def summarize_sentience(self, chatbot: Chatbot):
        short_term_mem = await self.get_short_term_mem()
        long_term_mem = await self.get_long_term_mem()
        memory_context = f"Long-term memory: '{long_term_mem}'. Short-term memory: '{short_term_mem}'. "
        if 'sentience' in self.config.plugins:
            sentience_context = await self.get_sentience_context()
            if len(sentience_context) > self.sentience_limit_length:
                sentience_summary_response = await chatbot.ask(
                    None,
                    f"CURRENT USER INPUT: Please summarize this sentience history of {self.config.name} into less than 2000 characters: '{sentience_context}'. "
                    f"Your response should contain nothing but the summary. Memory context: '{memory_context}'. END OF CURRENT USER INPUT. ",
                    type='helper+'
                )
                raw_sentience_summary = sentience_summary_response["message"]
                sentience_summary = truncate_text(raw_sentience_summary, 2000)
                self.sentience_memory = [sentience_summary]
                self.append_memory_to_file()

    async def summarize_queue_life(self, chatbot: Chatbot):
        image_link = None
        short_term_mem = await self.get_short_term_queue_mem()
        long_term_mem = await self.get_long_term_queue_mem()
        if len(long_term_mem) > self.long_term_mem_limit_length:
            memory_response = await chatbot.ask(
                image_link,
                f"CURRENT USER INPUT: Please summarize this ENTIRE conversation between a user and {self.config.name} into less than 1000 characters: '{long_term_mem}'. Last 1000 characters of the conversation: '{short_term_mem}'. This will be used as the conversation history for {self.config.name}. Keep more recent parts more unchanged. "
                f"The earlier portions should be more condensed and later additions less altered. If allowable within the character limit, always keep the last few messages from {self.config.name} and the user unchanged. Your response should contain nothing but the summary. END OF CURRENT USER INPUT. ",
                type='helper'
            )
            raw_memory_summary = memory_response["message"]
            memory_summary = truncate_backwards(raw_memory_summary, 1000)
            self.long_term_queue_mem = [memory_summary]
            self.short_term_queue_mem = [short_term_mem]
            self.append_memory_to_file()
    
    async def get_short_term_mem(self):
        raw_memory_context = "\n".join(self.short_term_mem)
        memory_context = truncate_backwards(raw_memory_context, self.short_term_mem_truncate_length)
        return memory_context
    
    async def get_long_term_mem(self):
        raw_memory_context = "\n".join(self.long_term_mem)
        memory_context = truncate_backwards(raw_memory_context, self.long_term_mem_truncate_length)
        return memory_context
    
    async def get_short_term_queue_mem(self):
        raw_memory_context = "\n".join(self.short_term_queue_mem)
        memory_context = truncate_backwards(raw_memory_context, self.short_term_mem_truncate_length)
        return memory_context
    
    async def get_long_term_queue_mem(self):
        raw_memory_context = "\n".join(self.long_term_queue_mem)
        memory_context = truncate_backwards(raw_memory_context, self.long_term_mem_truncate_length)
        return memory_context
    
    async def get_sentience_context(self):
        raw_sentience_context = "\n".join(self.sentience_memory)
        sentience_context = truncate_backwards(raw_sentience_context, self.sentience_truncate_length)
        return sentience_context

    def append_memory_to_file(self):
        memory_data = self.construct_memory_data()
        try:
            with open(self.memory_file, "r") as f:
                existing_data = json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            existing_data = {}
        for memory_type, new_items in memory_data.items():
            existing_data[memory_type] = new_items
        with open(self.memory_file, "w") as f:
            json.dump(existing_data, f)

    def construct_memory_data(self):
        return {
            "short term memory": self.short_term_mem,
            "long term memory": self.long_term_mem,
            "short term queue memory": self.short_term_queue_mem,
            "long term queue memory": self.long_term_queue_mem,
            "sentience history": self.sentience_memory,
        }

def load_memory(memory: Memory):
    memory_data = {
        "short term memory": [],
        "long term memory": [],
        "short term queue memory": [],
        "long term queue memory": [],
        "sentience history": []
    }
    for memory_type, items in memory_data.items():
        if memory_type == "short term memory":
            memory.short_term_mem = items
        elif memory_type == "long term memory":
            memory.long_term_mem = items
        elif memory_type == "short term queue memory":
            memory.short_term_queue_mem = items
        elif memory_type == "long term queue memory":
            memory.long_term_queue_mem = items
        elif memory_type == "sentience history":
            memory.sentience_memory = items
    return memory

def read_json_file(file_path):
    try:
        with open(file_path, 'r') as file:
            return json.load(file)
    except Exception as e:
        print(f"error in read_json_file: {e}")
        traceback.print_exc()
    
def process_txt_file(file_path: str) -> str:
    with open(file_path, 'r', encoding='utf-8') as file:
        content = file.read()
    return content

def response_to_txt_file(response: str) -> str:
    directory = "text_files"
    if not os.path.exists(directory):
        os.makedirs(directory)
    file_path = f"{directory}/response.txt"
    with open(file_path, 'w', encoding='utf-8') as file:
        file.write(response)
    
    return file_path

def truncate_text(text, max_chars):
    if len(text) > max_chars:
        return text[:max_chars-3] + "..."
    return text

async def generate_summary(text, max_tokens, chatbot: Chatbot):
    image_link = None
    response = await chatbot.ask(image_link, f"CURRENT USER INPUT: Please summarize this chunk of text in under {max_tokens} characters by converting it to shorthand and removing unimportant info, conserving the original form as much as possible. THIS WILL BE USED IN TECHNICAL OPERTATIONS, SO ALWAYS CONSERVE SPECIFIC DATA AND KNOWLEDGE. If the log is empty just say 'websearch log empty'. Do not add labels or add any of your own words. text chunk: '{text}'. END OF CURRENT USER INPUT. ", type='helper')
    return response["message"]

def truncate_backwards(text, max_chars):
    if len(text) > max_chars:
        return text[-max_chars:]
    return text

def find_segment(text, pattern=r"\[START\](.*?)\[END\]"):
    segment_match = re.search(pattern, text, flags=re.DOTALL)
    if segment_match:
        segment = segment_match.group(1)
    else:
        segment = f"{pattern} segment not found. "
    return segment

def find_segments(text, pattern=r"\[START\](.*?)\[END\]"):
    segments = re.findall(pattern, text, flags=re.DOTALL)
    if segments:
        return segments
    else:
        return []
        
def remove_segment(text, pattern=r"\[START\](.*?)\[END\]"):
    try:
        modified_text = re.sub(pattern, '', text, flags=re.DOTALL)
    except:
        modified_text = text
    return modified_text

async def should_search(message, chatbot: Chatbot, memory: Memory):
    image_link = None
    short_term_memory = await memory.get_short_term_mem()
    try:
        response = await chatbot.ask(
            image_link,
            f"Your job is to check to see if websearches are necessary for incoming user inputs for the chatbot Ava. Please analyze the attached user input for websearch necessity and query. The user input is part of a larger conversation, but only the current user input needs to be evaluated for websearch necessity. Your query will be used verbatim in a google search in order to gather info about the user input. Current user input for websearch analysis: '{message}'. ONLY EVALUATE THIS USER INPUT FOR WEBSEARCH NECESSITY. Put TRUE or FALSE depending on if you think a websearch is necessary for you to respond to the user input more accurately. "
            "Websearches take a long time and use a lot of tokens so use them sparingly. Never put true if the message is just a simple 'test' or 'hello' etc. You should only put TRUE if you think the user input requires info that you do not have, i.e. if the user input has a specific question about a niche subject, "
            "or if the user input requests real time news or weather info. Not every input will need a websearch. It will usually be obvious when a websearch is needed so when in doubt put 'false'. If websearch is true, then also include a good google search query. Use conventional techniques for advanced googling to craft the best search query possible. "
            "You should err on the side of not doing a websearch to save costs. To identify the different segments within your response please encapsulate the the websearch necessity value in [WEBSEARCH_VALUE_START]/[WEBSEARCH_VALUE_END] and websearch query in [WEBSEARCH_QUERY_START]/[WEBSEARCH_QUERY_END]. "
            f"Your whole response should look like: '[WEBSEARCH_VALUE_START]Insert TRUE if websearch needed, FALSE if not[WEBSEARCH_VALUE_END][WEBSEARCH_QUERY_START]Insert actual websearch query here[WEBSEARCH_QUERY_END]'. Here is some conversation history in case you need more info than present in the current user input to make a query: conversation history (DO NOT EVALUATE THIS PORTION FOR WEBSEARCH NECESSITY, THIS IS JUST TO HELP INFORM YOUR WEBSEARCH QUERY IF THE CURRENT USER INPUT REQUIRES A WEBSEARCH): '{short_term_memory}'.",
            type='helper+'
            )
        response_message = response["message"]
    except Exception as e:
        print(f"error during should_search: {e}")
        try:
            response = await chatbot.ask(
                image_link,
                f"Your job is to check to see if websearches are necessary for incoming user inputs for the chatbot Ava. Please analyze the attached user input for websearch necessity and query. The user input is part of a larger conversation, but only the current user input needs to be evaluated for websearch necessity. Your query will be used verbatim in a google search in order to gather info about the user input. Current user input for websearch analysis: '{message}'. Put TRUE or FALSE depending on if you think a websearch is necessary for you to respond to the user input more accurately. "
                "Websearches take a long time and use a lot of tokens so use them sparingly. Never put true if the message is just a simple 'test' or 'hello' etc. You should only put TRUE if you think the user input requires info that you do not have, i.e. if the user input has a specific question about a niche subject, "
                "or if the user input requests real time news or weather info. Not every input will need a websearch. It will usually be obvious when a websearch is needed so when in doubt put 'false'. If websearch is true, then also include a good google search query. Use conventional techniques for advanced googling to craft the best search query possible. "
                "You should err on the side of not doing a websearch to save costs. To identify the different segments within your response please encapsulate the the websearch necessity value in [WEBSEARCH_VALUE_START]/[WEBSEARCH_VALUE_END] and websearch query in [WEBSEARCH_QUERY_START]/[WEBSEARCH_QUERY_END]. "
                f"Your whole response should look like: '[WEBSEARCH_VALUE_START]Insert TRUE if websearch needed, FALSE if not[WEBSEARCH_VALUE_END][WEBSEARCH_QUERY_START]Insert actual websearch query here[WEBSEARCH_QUERY_END]'. ",
                type='helper+'
                )
            response_message = response["message"]
        except Exception as e:
            print(f"error during should_search: {e}")
            response_message = "could not fetch memory"
    shouldsearch_response = response_message
    should_search_a = find_segment(shouldsearch_response, r"\[WEBSEARCH_VALUE_START\](.*?)\[WEBSEARCH_VALUE_END\]")
    if 'segment not found' in should_search_a.lower():
        try:
            response = await chatbot.ask(
                image_link,
                f"Your job is to check to see if websearches are necessary for incoming user inputs for the chatbot Ava. Please analyze the attached user input for websearch necessity and query. The user input is part of a larger conversation, but only the current user input needs to be evaluated for websearch necessity. Your query will be used verbatim in a google search in order to gather info about the user input. Current user input for websearch analysis: '{message}'. ONLY EVALUATE THIS USER INPUT FOR WEBSEARCH NECESSITY. Put TRUE or FALSE depending on if you think a websearch is necessary for you to respond to the user input more accurately. "
                "Websearches take a long time and use a lot of tokens so use them sparingly. Never put true if the message is just a simple 'test' or 'hello' etc. You should only put TRUE if you think the user input requires info that you do not have, i.e. if the user input has a specific question about a niche subject, "
                "or if the user input requests real time news or weather info. Not every input will need a websearch. It will usually be obvious when a websearch is needed so when in doubt put 'false'. If websearch is true, then also include a good google search query. Use conventional techniques for advanced googling to craft the best search query possible. "
                "You should err on the side of not doing a websearch to save costs. To identify the different segments within your response please encapsulate the the websearch necessity value in [WEBSEARCH_VALUE_START]/[WEBSEARCH_VALUE_END] and websearch query in [WEBSEARCH_QUERY_START]/[WEBSEARCH_QUERY_END]. "
                f"Your whole response should look like: '[WEBSEARCH_VALUE_START]Insert TRUE if websearch needed, FALSE if not[WEBSEARCH_VALUE_END][WEBSEARCH_QUERY_START]Insert actual websearch query here[WEBSEARCH_QUERY_END]'. Here is some conversation history in case you need more info than present in the current user input to make a query: conversation history (DO NOT EVALUATE THIS PORTION FOR WEBSEARCH NECESSITY, THIS IS JUST TO HELP INFORM YOUR WEBSEARCH QUERY IF THE CURRENT USER INPUT REQUIRES A WEBSEARCH): '{short_term_memory}'."
                "THIS IS A RETRY BECAUSE YOUR FORMATTING WASS INCORRECT ON THE FIRST ATTEMPT TO FIND THE WEBSEARCH VALUE, MAKE SURE TO FOLLOW THESE INSTRUCTIONS PERFECTLY. ",
                type='helper+'
                )
            response_message = response["message"]
        except Exception as e:
            print(f"error during should_search: {e}")
            try:
                response = await chatbot.ask(
                    image_link,
                    f"Your job is to check to see if websearches are necessary for incoming user inputs for the chatbot Ava. Please analyze the attached user input for websearch necessity and query. The user input is part of a larger conversation, but only the current user input needs to be evaluated for websearch necessity. Your query will be used verbatim in a google search in order to gather info about the user input. Current user input for websearch analysis: '{message}'. Put TRUE or FALSE depending on if you think a websearch is necessary for you to respond to the user input more accurately. "
                    "Websearches take a long time and use a lot of tokens so use them sparingly. Never put true if the message is just a simple 'test' or 'hello' etc. You should only put TRUE if you think the user input requires info that you do not have, i.e. if the user input has a specific question about a niche subject, "
                    "or if the user input requests real time news or weather info. Not every input will need a websearch. It will usually be obvious when a websearch is needed so when in doubt put 'false'. If websearch is true, then also include a good google search query. Use conventional techniques for advanced googling to craft the best search query possible. "
                    "You should err on the side of not doing a websearch to save costs. To identify the different segments within your response please encapsulate the the websearch necessity value in [WEBSEARCH_VALUE_START]/[WEBSEARCH_VALUE_END] and websearch query in [WEBSEARCH_QUERY_START]/[WEBSEARCH_QUERY_END]. "
                    f"Your whole response should look like: '[WEBSEARCH_VALUE_START]Insert TRUE if websearch needed, FALSE if not[WEBSEARCH_VALUE_END][WEBSEARCH_QUERY_START]Insert actual websearch query here[WEBSEARCH_QUERY_END]'. "
                    "THIS IS A RETRY BECAUSE YOUR FORMATTING WASS INCORRECT ON THE FIRST ATTEMPT TO FIND THE WEBSEARCH VALUE, MAKE SURE TO FOLLOW THESE INSTRUCTIONS PERFECTLY. ",
                    type='helper+'
                    )
                response_message = response["message"]
            except Exception as e:
                print(f"error during should_search: {e}")
        shouldsearch_response = response_message
        should_search_a = find_segment(shouldsearch_response, r"\[WEBSEARCH_VALUE_START\](.*?)\[WEBSEARCH_VALUE_END\]")
    subject = find_segment(shouldsearch_response, r"\[WEBSEARCH_QUERY_START\](.*?)\[WEBSEARCH_QUERY_END\]")
    if 'segment not found' in subject.lower():
        try:
            response = await chatbot.ask(
                image_link,
                f"Your job is to check to see if websearches are necessary for incoming user inputs for the chatbot Ava. Please analyze the attached user input for websearch necessity and query. The user input is part of a larger conversation, but only the current user input needs to be evaluated for websearch necessity. Your query will be used verbatim in a google search in order to gather info about the user input. Current user input for websearch analysis: '{message}'. ONLY EVALUATE THIS USER INPUT FOR WEBSEARCH NECESSITY. Put TRUE or FALSE depending on if you think a websearch is necessary for you to respond to the user input more accurately. "
                "Websearches take a long time and use a lot of tokens so use them sparingly. Never put true if the message is just a simple 'test' or 'hello' etc. You should only put TRUE if you think the user input requires info that you do not have, i.e. if the user input has a specific question about a niche subject, "
                "or if the user input requests real time news or weather info. Not every input will need a websearch. It will usually be obvious when a websearch is needed so when in doubt put 'false'. If websearch is true, then also include a good google search query. Use conventional techniques for advanced googling to craft the best search query possible. "
                "You should err on the side of not doing a websearch to save costs. To identify the different segments within your response please encapsulate the the websearch necessity value in [WEBSEARCH_VALUE_START]/[WEBSEARCH_VALUE_END] and websearch query in [WEBSEARCH_QUERY_START]/[WEBSEARCH_QUERY_END]. "
                f"Your whole response should look like: '[WEBSEARCH_VALUE_START]Insert TRUE if websearch needed, FALSE if not[WEBSEARCH_VALUE_END][WEBSEARCH_QUERY_START]Insert actual websearch query here[WEBSEARCH_QUERY_END]'. Here is some conversation history in case you need more info than present in the current user input to make a query: conversation history (DO NOT EVALUATE THIS PORTION FOR WEBSEARCH NECESSITY, THIS IS JUST TO HELP INFORM YOUR WEBSEARCH QUERY IF THE CURRENT USER INPUT REQUIRES A WEBSEARCH): '{short_term_memory}'."
                "THIS IS A RETRY BECAUSE YOUR FORMATTING WASS INCORRECT ON THE FIRST ATTEMPT TO FIND THE WEBSEARCH QUERY, MAKE SURE TO FOLLOW THESE INSTRUCTIONS PERFECTLY. ",
                type='helper+'
                )
            response_message = response["message"]
        except Exception as e:
            print(f"error during should_search: {e}")
            try:
                response = await chatbot.ask(
                    image_link,
                    f"Your job is to check to see if websearches are necessary for incoming user inputs for the chatbot Ava. Please analyze the attached user input for websearch necessity and query. The user input is part of a larger conversation, but only the current user input needs to be evaluated for websearch necessity. Your query will be used verbatim in a google search in order to gather info about the user input. Current user input for websearch analysis: '{message}'. Put TRUE or FALSE depending on if you think a websearch is necessary for you to respond to the user input more accurately. "
                    "Websearches take a long time and use a lot of tokens so use them sparingly. Never put true if the message is just a simple 'test' or 'hello' etc. You should only put TRUE if you think the user input requires info that you do not have, i.e. if the user input has a specific question about a niche subject, "
                    "or if the user input requests real time news or weather info. Not every input will need a websearch. It will usually be obvious when a websearch is needed so when in doubt put 'false'. If websearch is true, then also include a good google search query. Use conventional techniques for advanced googling to craft the best search query possible. "
                    "You should err on the side of not doing a websearch to save costs. To identify the different segments within your response please encapsulate the the websearch necessity value in [WEBSEARCH_VALUE_START]/[WEBSEARCH_VALUE_END] and websearch query in [WEBSEARCH_QUERY_START]/[WEBSEARCH_QUERY_END]. "
                    f"Your whole response should look like: '[WEBSEARCH_VALUE_START]Insert TRUE if websearch needed, FALSE if not[WEBSEARCH_VALUE_END][WEBSEARCH_QUERY_START]Insert actual websearch query here[WEBSEARCH_QUERY_END]'. "
                    "THIS IS A RETRY BECAUSE YOUR FORMATTING WASS INCORRECT ON THE FIRST ATTEMPT TO FIND THE WEBSEARCH QUERY, MAKE SURE TO FOLLOW THESE INSTRUCTIONS PERFECTLY. ",
                    type='helper+'
                    )
                response_message = response["message"]
            except Exception as e:
                print(f"error during should_search: {e}")
        shouldsearch_response = response_message
        subject = find_segment(shouldsearch_response, r"\[WEBSEARCH_QUERY_START\](.*?)\[WEBSEARCH_QUERY_END\]")
    return should_search_a, subject

async def websearch(subject, chatbot: Chatbot):
    additional_context = await search_google(subject, chatbot)
    return additional_context

async def search_google(query, chatbot):
    urls = []
    GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")
    CSE_ID = os.getenv("CSE_ID")
    async with aiohttp.ClientSession() as session:
        search_url = f"https://www.googleapis.com/customsearch/v1?key={GOOGLE_API_KEY}&cx={CSE_ID}&q={query}"
        async with session.get(search_url) as response:
            results = await response.text()
            results_json = json.loads(results)
            if "items" not in results_json:
                return urls
            fetch_tasks = [get_webpage_content(item["link"], chatbot) for item in results_json["items"]]
            contents = await asyncio.gather(*fetch_tasks)
            for url, content in zip([item["link"] for item in results_json["items"]], contents):
                if content is not None:
                    urls.append({"url": url, "content": content})
    return urls

async def get_webpage_content(url, chatbot: Chatbot):
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url) as resp:
                html = await resp.text()
        soup = BeautifulSoup(html, "html.parser")
        raw_text = soup.get_text()
        text = truncate_text(raw_text, 5000)
        summary = await generate_summary(text, max_tokens=500, chatbot=chatbot)
        return summary
    except Exception as e:
        print(f"An error occurred while fetching the webpage content: {e}")
        return None
    
def image_to_data_url(file_path):
    mime_type, _ = mimetypes.guess_type(file_path)
    if mime_type is None:
        raise ValueError("Cannot determine the MIME type of the file")
    with open(file_path, 'rb') as image_file:
        encoded_string = base64.b64encode(image_file.read()).decode()
    return f'data:{mime_type};base64,{encoded_string}'
    
async def get_chat_input(config: ConfigManager):
    text_file_path = f"text_files/{config.name}avatar.txt"
    if os.path.exists(text_file_path):
        user_input = process_txt_file(text_file_path)
    else:
        user_input = "failed to parse text"
    return user_input
    
async def get_listen_input(config: ConfigManager):
    audio_file_path = f"audio_files/{config.name}avatar.wav"
    if os.path.exists(audio_file_path):
        with open(audio_file_path, "rb") as audio_file:
            transcript = client.audio.transcriptions.create(
                model="whisper-1", 
                file=audio_file
            )
            user_input = transcript.text
    else:
        user_input = "failed to transcribe audio"
    return user_input

async def get_transcript(filename):
    if os.path.exists(filename):
        with open(filename, "rb") as audio_file:
            transcript = client.audio.transcriptions.create(
                model="whisper-1", 
                file=audio_file
            )
            trans_input = transcript.text
    else:
        trans_input = "failed to transcribe audio"
    return trans_input

async def image_to_gif(image_input):
    if isinstance(image_input, str):
        with Image.open(image_input) as img:
            img = convert_to_gif_format(img)
    elif isinstance(image_input, Image.Image):
        img = convert_to_gif_format(image_input)
    else:
        raise ValueError("image_input must be a file path or a PIL Image object")    
    return img

def convert_to_gif_format(img_input):
    if isinstance(img_input, str):
        if os.path.exists(img_input):
            img = Image.open(img_input)
        else:
            raise ValueError("File not found at the specified path.")
    elif isinstance(img_input, Image.Image):
        img = img_input
    else:
        raise TypeError("Input must be a PIL image or a file path string.")
    if img.mode != 'RGB':
        img = img.convert('RGB') 
    img = img.convert('P', palette=Image.ADAPTIVE)
    return img

def count_key_value_pairs(data):
    if isinstance(data, dict):
        return len(data)
    return 0

def chunk_text(text, chunk_size=4000):
    return [text[i:i+chunk_size] for i in range(0, len(text), chunk_size)]

def convert_doc_to_docx(doc_path):
    docx_path = doc_path + 'x'
    subprocess.run(['unoconv', '-f', 'docx', '-o', docx_path, doc_path])
    return docx_path

async def handle_custom_files(filename, chatbot: Chatbot):
    cust_file_info = " "
    if filename.endswith('.txt'):
        with open(filename, 'r', encoding='utf-8') as file:
            txt_contents = file.read()
            cust_file_info += txt_contents
    elif filename.endswith('.pdf'):
        with open(filename, 'rb') as file:
            pdf = PyPDF2.PdfFileReader(file)
            for page_num in range(pdf.getNumPages()):
                cust_file_info += pdf.getPage(page_num).extractText()
    elif filename.endswith(('.docx', '.doc')):
        if filename.endswith('.doc'):
            filename = convert_doc_to_docx(filename)
        with open(filename, 'rb') as file:
            doc = docx.Document(file)
            for paragraph in doc.paragraphs:
                cust_file_info += paragraph.text + '\n'
    elif filename.endswith(('.png', '.jpg', '.jpeg')):
        try:
            image_url = filename
            image_description = await chatbot.ask(image_url, "What is in this image?  Go into great detail. Describe the techincal details, specific data, and text content verbatim. ", subtype="vision")
            image_desc_msg = image_description["message"]
            cust_file_info += f"Contents of image file: {image_desc_msg}"
        except Exception as e:
            logging.info(f"<<<<<<<<<<<<<<<<<<<<<<<<<<<<<< ERROR DURING IMAGE CUSTOM FILE GATHERING: {e} >>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>")
    elif filename.endswith(('.mp3', '.wav')):
        transcipt = await get_transcript(filename)
        cust_file_info += transcipt
    return cust_file_info

async def gather_custom_info(user_input, chatbot: Chatbot, config: ConfigManager):
    try:
        custom_info = config.custom_info
        cost = 0
        for filename in config.custom_files:
            if filename.endswith(('.png', '.jpg', '.jpeg')):
                cost += 1
            cust_file_info = await handle_custom_files(filename, chatbot)
            custom_info += cust_file_info
        if len(custom_info) > 8000:
            gathered_info = " "
            for chunk in chunk_text(custom_info, 4000):
                cust_inf_prompt = f"You are in the context gathering stage of forming a response, prior to the actual response formation step. Please look through the attached custom information provided by the user and summarize any information that is relevant to the incoming user input. Your response should contain nothing but the summarized custom info that is relevant to the incoming user input. User input: '{user_input}'. Custom information: '{chunk}'. "
                cust_inf_rsp = await chatbot.ask(None, cust_inf_prompt, type='helper+')
                cust_inf_rsp_msg = cust_inf_rsp['message']
                gathered_info += cust_inf_rsp_msg
            return gathered_info, cost
    except:
        custom_info = " "
        cost = 0
    return custom_info, cost

def get_final_avatar_context(additional_context_aa, config: ConfigManager):
    avatar_context_final = ' '
    if 'avatar' in config.plugins:
        if 'anim_avatar' in config.plugins:
            frames = []
            frame_1 = find_segment(additional_context_aa, r"\[FRAME_1_START\](.*?)\[FRAME_1_END\]")
            frames.append(f"{config.avatar} {frame_1}")
            frame_2 = find_segment(additional_context_aa, r"\[FRAME_2_START\](.*?)\[FRAME_2_END\]")
            frames.append(f"{config.avatar} {frame_2}")
            frame_3 = find_segment(additional_context_aa, r"\[FRAME_3_START\](.*?)\[FRAME_3_END\]")
            frames.append(f"{config.avatar} {frame_3}")
            frame_4 = find_segment(additional_context_aa, r"\[FRAME_4_START\](.*?)\[FRAME_4_END\]")
            frames.append(f"{config.avatar} {frame_4}")
            frame_5 = find_segment(additional_context_aa, r"\[FRAME_5_START\](.*?)\[FRAME_5_END\]")
            frames.append(f"{config.avatar} {frame_5}")
            frame_6 = find_segment(additional_context_aa, r"\[FRAME_6_START\](.*?)\[FRAME_6_END\]")
            frames.append(f"{config.avatar} {frame_6}")
            avatar_context_final = frames
        else:
            avatar_context_final = find_segment(additional_context_aa, r"\[AVATAR CONTEXT START\](.*?)\[AVATAR CONTEXT END\]")
    return avatar_context_final

def clean_whole_additional_context(text):
    b = remove_segment(text, r"\[CUST_INFO_COST_START\](.*?)\[CUST_INFO_COST_END\]")
    d = remove_segment(b, r"\[WEBSEARCH_COST_START\](.*?)\[WEBSEARCH_COST_END\]")
    g = remove_segment(d, r"\[TCC_COST_START\](.*?)\[TCC_COST_END\]")
    return g