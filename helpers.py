from bs4 import BeautifulSoup
import aiohttp
import json
import os
import os
from config_module import ConfigManager
from chatbot import Chatbot
import shutil
import re
import traceback
import asyncio
from sentience_module import get_sentience_core
from openai_module import client

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
        self.long_term_mem_truncate_length = 4500
        self.sentience_limit_length = 4000
        self.sentience_truncate_length = 4500
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
        short_term_mem = await self.get_short_term_mem()
        long_term_mem = await self.get_long_term_mem()
        #print(f"short_term_mem before summary: {short_term_mem}")
        #print(f"long_term_mem before summary: {long_term_mem}")
        if len(long_term_mem) > self.long_term_mem_limit_length:
            print("summarizing memory")
            memory_response = await chatbot.ask(
                f"CURRENT USER INPUT: Please summarize this ENTIRE conversation between a user and {self.config.name} into less than 2000 characters: '{long_term_mem}'. Last 1000 characters of the conversation: '{short_term_mem}'. This will be used as the conversation history for {self.config.name}. Keep more recent parts more unchanged. "
                f"The earlier portions should be more condensed and later additions less altered. If allowable within the character limit, always keep the last few messages from {self.config.name} and the user unchanged. Your response should contain nothing but the summary. END OF CURRENT USER INPUT. ",
                type='helper'
            )
            raw_memory_summary = memory_response["message"]
            memory_summary = truncate_backwards(raw_memory_summary, 2000)
            #print(f"memory_summary after summary: {memory_summary}")
            self.long_term_mem = [memory_summary]
            self.short_term_mem = [short_term_mem]
            self.append_memory_to_file()
        if 'sentience' in self.config.plugins:
            sentience_context = await self.get_sentience_context()
            memory_context = f"Long-term memory: '{long_term_mem}'. Short-term memory: '{short_term_mem}'. "
            sentience_core = await get_sentience_core(sentience_context, memory_context, chatbot)
            self.add_sentience(sentience_core)
            #print(f"sentience_context before summary: {sentience_context}")
            if len(sentience_context) > self.sentience_limit_length:
                #print("summarizing memory")
                sentience_summary_response = await chatbot.ask(
                    f"CURRENT USER INPUT: Please summarize this sentience history of {self.config.name} into less than 1000 characters: '{sentience_context}'. "
                    "Your response should contain nothing but the summary. END OF CURRENT USER INPUT. ",
                    type='helper'
                )
                raw_sentience_summary = sentience_summary_response["message"]
                sentience_summary = truncate_text(raw_sentience_summary, 1000)
                #print(f"sentience_summary after summary: {sentience_summary}")
                self.sentience_memory = [sentience_summary]
                self.append_memory_to_file()

    async def summarize_queue_life(self, chatbot: Chatbot):
        short_term_mem = await self.get_short_term_queue_mem()
        long_term_mem = await self.get_long_term_queue_mem()
        #print(f"short_term_mem before summary: {short_term_mem}")
        #print(f"long_term_mem before summary: {long_term_mem}")
        if len(long_term_mem) > self.long_term_mem_limit_length:
            #print("summarizing memory")
            memory_response = await chatbot.ask(
                f"CURRENT USER INPUT: Please summarize this ENTIRE conversation between a user and {self.config.name} into less than 1000 characters: '{long_term_mem}'. Last 1000 characters of the conversation: '{short_term_mem}'. This will be used as the conversation history for {self.config.name}. Keep more recent parts more unchanged. "
                f"The earlier portions should be more condensed and later additions less altered. If allowable within the character limit, always keep the last few messages from {self.config.name} and the user unchanged. Your response should contain nothing but the summary. END OF CURRENT USER INPUT. ",
                type='helper'
            )
            raw_memory_summary = memory_response["message"]
            memory_summary = truncate_backwards(raw_memory_summary, 1000)
            #print(f"memory_summary after summary: {memory_summary}")
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
        #print(f"entering append_mem_to_file")
        memory_data = self.construct_memory_data()
        #print(f"memory before opening memory json file: {memory_data}")
        try:
            with open(self.memory_file, "r") as f:
                existing_data = json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            existing_data = {}
            print(f"Warning: Issue with reading file, starting with empty memory for {self.memory_file}")
        #print(f"existing contents of memory json file before extending new data: {existing_data}")
        for memory_type, new_items in memory_data.items():
            existing_data[memory_type] = new_items
        #print(f"existing data after adding new data: {existing_data}")
        with open(self.memory_file, "w") as f:
            json.dump(existing_data, f)

    def construct_memory_data(self):
        # Consolidated memory data construction
        return {
            "short term memory": self.short_term_mem,
            "long term memory": self.long_term_mem,
            "short term queue memory": self.short_term_queue_mem,
            "long term queue memory": self.long_term_queue_mem,
            "sentience history": self.sentience_memory,
        }

def load_memory(memory: Memory):
    memory_data = f'{memory.config.name}_memory'
    if memory_data is None:
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

def display_file(file_name, config_name, type):
    file_extension = os.path.splitext(file_name)[1]  # Get the file extension
    destination_path = f'media/{config_name}{type}{file_extension}'  # Use the config_name and extension
    
    shutil.copy(file_name, destination_path)
    print(f"copied {file_name} to {destination_path}")

async def generate_summary(text, max_tokens, chatbot: Chatbot):
    response = await chatbot.ask(f"CURRENT USER INPUT: Please summarize this chunk of text in under {max_tokens} characters by converting it to shorthand and removing unimportant info, conserving the original form as much as possible. If the log is empty just say 'websearch log empty'. Do not add labels or add any of your own words. text chunk: '{text}'. END OF CURRENT USER INPUT. ", type='helper')
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

def remove_segment(text, pattern=r"\[START\](.*?)\[END\]"):
    modified_text = re.sub(pattern, '', text, flags=re.DOTALL)
    return modified_text

async def should_search(message, chatbot: Chatbot, memory: Memory):
    short_term_memory = await memory.get_short_term_mem()
    try:
        response = await chatbot.ask(
            f"Your job is to check to see if websearches are necessary for incoming user inputs for the chatbot Ava. Please analyze the attached user input for websearch necessity and query. The user input is part of a larger conversation, but only the current user input needs to be evaluated for websearch necessity. Your query will be used verbatim in a google search in order to gather info about the user input. Current user input for websearch analysis: '{message}'. ONLY EVALUATE THIS USER INPUT FOR WEBSEARCH NECESSITY. Put TRUE or FALSE depending on if you think a websearch is necessary for you to respond to the user input more accurately. "
            "Websearches take a long time and use a lot of tokens so use them sparingly. Never put true if the message is just a simple 'test' or 'hello' etc. You should only put TRUE if you think the user input requires info that you do not have, i.e. if the user input has a specific question about a niche subject, "
            "or if the user input requests real time news or weather info. Not every input will need a websearch. It will usually be obvious when a websearch is needed so when in doubt put 'false'. If websearch is true, then also include a good google search query. Use conventional techniques for advanced googling to craft the best search query possible. "
            "You should err on the side of not doing a websearch to save costs. To identify the different segments within your response please encapsulate the the websearch necessity value in [WEBSEARCH_VALUE_START]/[WEBSEARCH_VALUE_END] and websearch query in [WEBSEARCH_QUERY_START]/[WEBSEARCH_QUERY_END]. "
            f"Your whole response should look like: '[WEBSEARCH_VALUE_START]Insert TRUE if websearch needed, FALSE if not[WEBSEARCH_VALUE_END][WEBSEARCH_QUERY_START]Insert actual websearch query here[WEBSEARCH_QUERY_END]'. Here is some conversation history in case you need more info than present in the current user input to make a query: conversation history (DO NOT EVALUATE THIS PORTION FOR WEBSEARCH NECESSITY, THIS IS JUST TO HELP INFORM YOUR WEBSEARCH QUERY IF THE CURRENT USER INPUT REQUIRES A WEBSEARCH): '{short_term_memory}'.",
            type='helper+'
            )
    except Exception as e:
        print(f"error during should_search: {e}")
        try:
            response = await chatbot.ask(
                f"Your job is to check to see if websearches are necessary for incoming user inputs for the chatbot Ava. Please analyze the attached user input for websearch necessity and query. The user input is part of a larger conversation, but only the current user input needs to be evaluated for websearch necessity. Your query will be used verbatim in a google search in order to gather info about the user input. Current user input for websearch analysis: '{message}'. Put TRUE or FALSE depending on if you think a websearch is necessary for you to respond to the user input more accurately. "
                "Websearches take a long time and use a lot of tokens so use them sparingly. Never put true if the message is just a simple 'test' or 'hello' etc. You should only put TRUE if you think the user input requires info that you do not have, i.e. if the user input has a specific question about a niche subject, "
                "or if the user input requests real time news or weather info. Not every input will need a websearch. It will usually be obvious when a websearch is needed so when in doubt put 'false'. If websearch is true, then also include a good google search query. Use conventional techniques for advanced googling to craft the best search query possible. "
                "You should err on the side of not doing a websearch to save costs. To identify the different segments within your response please encapsulate the the websearch necessity value in [WEBSEARCH_VALUE_START]/[WEBSEARCH_VALUE_END] and websearch query in [WEBSEARCH_QUERY_START]/[WEBSEARCH_QUERY_END]. "
                f"Your whole response should look like: '[WEBSEARCH_VALUE_START]Insert TRUE if websearch needed, FALSE if not[WEBSEARCH_VALUE_END][WEBSEARCH_QUERY_START]Insert actual websearch query here[WEBSEARCH_QUERY_END]'. ",
                type='helper+'
                )
        except Exception as e:
            print(f"error during should_search: {e}")
    whole_memory_summary = response["message"]
    should_search_a = find_segment(whole_memory_summary, r"\[WEBSEARCH_VALUE_START\](.*?)\[WEBSEARCH_VALUE_END\]")
    if 'segment not found' in should_search_a.lower():
        try:
            response = await chatbot.ask(
                f"Your job is to check to see if websearches are necessary for incoming user inputs for the chatbot Ava. Please analyze the attached user input for websearch necessity and query. The user input is part of a larger conversation, but only the current user input needs to be evaluated for websearch necessity. Your query will be used verbatim in a google search in order to gather info about the user input. Current user input for websearch analysis: '{message}'. ONLY EVALUATE THIS USER INPUT FOR WEBSEARCH NECESSITY. Put TRUE or FALSE depending on if you think a websearch is necessary for you to respond to the user input more accurately. "
                "Websearches take a long time and use a lot of tokens so use them sparingly. Never put true if the message is just a simple 'test' or 'hello' etc. You should only put TRUE if you think the user input requires info that you do not have, i.e. if the user input has a specific question about a niche subject, "
                "or if the user input requests real time news or weather info. Not every input will need a websearch. It will usually be obvious when a websearch is needed so when in doubt put 'false'. If websearch is true, then also include a good google search query. Use conventional techniques for advanced googling to craft the best search query possible. "
                "You should err on the side of not doing a websearch to save costs. To identify the different segments within your response please encapsulate the the websearch necessity value in [WEBSEARCH_VALUE_START]/[WEBSEARCH_VALUE_END] and websearch query in [WEBSEARCH_QUERY_START]/[WEBSEARCH_QUERY_END]. "
                f"Your whole response should look like: '[WEBSEARCH_VALUE_START]Insert TRUE if websearch needed, FALSE if not[WEBSEARCH_VALUE_END][WEBSEARCH_QUERY_START]Insert actual websearch query here[WEBSEARCH_QUERY_END]'. Here is some conversation history in case you need more info than present in the current user input to make a query: conversation history (DO NOT EVALUATE THIS PORTION FOR WEBSEARCH NECESSITY, THIS IS JUST TO HELP INFORM YOUR WEBSEARCH QUERY IF THE CURRENT USER INPUT REQUIRES A WEBSEARCH): '{short_term_memory}'."
                "THIS IS A RETRY BECAUSE YOUR FORMATTING WASS INCORRECT ON THE FIRST ATTEMPT TO FIND THE WEBSEARCH VALUE, MAKE SURE TO FOLLOW THESE INSTRUCTIONS PERFECTLY. ",
                type='helper+'
                )
        except Exception as e:
            print(f"error during should_search: {e}")
            try:
                response = await chatbot.ask(
                    f"Your job is to check to see if websearches are necessary for incoming user inputs for the chatbot Ava. Please analyze the attached user input for websearch necessity and query. The user input is part of a larger conversation, but only the current user input needs to be evaluated for websearch necessity. Your query will be used verbatim in a google search in order to gather info about the user input. Current user input for websearch analysis: '{message}'. Put TRUE or FALSE depending on if you think a websearch is necessary for you to respond to the user input more accurately. "
                    "Websearches take a long time and use a lot of tokens so use them sparingly. Never put true if the message is just a simple 'test' or 'hello' etc. You should only put TRUE if you think the user input requires info that you do not have, i.e. if the user input has a specific question about a niche subject, "
                    "or if the user input requests real time news or weather info. Not every input will need a websearch. It will usually be obvious when a websearch is needed so when in doubt put 'false'. If websearch is true, then also include a good google search query. Use conventional techniques for advanced googling to craft the best search query possible. "
                    "You should err on the side of not doing a websearch to save costs. To identify the different segments within your response please encapsulate the the websearch necessity value in [WEBSEARCH_VALUE_START]/[WEBSEARCH_VALUE_END] and websearch query in [WEBSEARCH_QUERY_START]/[WEBSEARCH_QUERY_END]. "
                    f"Your whole response should look like: '[WEBSEARCH_VALUE_START]Insert TRUE if websearch needed, FALSE if not[WEBSEARCH_VALUE_END][WEBSEARCH_QUERY_START]Insert actual websearch query here[WEBSEARCH_QUERY_END]'. "
                    "THIS IS A RETRY BECAUSE YOUR FORMATTING WASS INCORRECT ON THE FIRST ATTEMPT TO FIND THE WEBSEARCH VALUE, MAKE SURE TO FOLLOW THESE INSTRUCTIONS PERFECTLY. ",
                    type='helper+'
                    )
            except Exception as e:
                print(f"error during should_search: {e}")
        whole_memory_summary = response["message"]
        should_search_a = find_segment(whole_memory_summary, r"\[WEBSEARCH_VALUE_START\](.*?)\[WEBSEARCH_VALUE_END\]")
    subject = find_segment(whole_memory_summary, r"\[WEBSEARCH_QUERY_START\](.*?)\[WEBSEARCH_QUERY_END\]")
    if 'segment not found' in subject.lower():
        try:
            response = await chatbot.ask(
                f"Your job is to check to see if websearches are necessary for incoming user inputs for the chatbot Ava. Please analyze the attached user input for websearch necessity and query. The user input is part of a larger conversation, but only the current user input needs to be evaluated for websearch necessity. Your query will be used verbatim in a google search in order to gather info about the user input. Current user input for websearch analysis: '{message}'. ONLY EVALUATE THIS USER INPUT FOR WEBSEARCH NECESSITY. Put TRUE or FALSE depending on if you think a websearch is necessary for you to respond to the user input more accurately. "
                "Websearches take a long time and use a lot of tokens so use them sparingly. Never put true if the message is just a simple 'test' or 'hello' etc. You should only put TRUE if you think the user input requires info that you do not have, i.e. if the user input has a specific question about a niche subject, "
                "or if the user input requests real time news or weather info. Not every input will need a websearch. It will usually be obvious when a websearch is needed so when in doubt put 'false'. If websearch is true, then also include a good google search query. Use conventional techniques for advanced googling to craft the best search query possible. "
                "You should err on the side of not doing a websearch to save costs. To identify the different segments within your response please encapsulate the the websearch necessity value in [WEBSEARCH_VALUE_START]/[WEBSEARCH_VALUE_END] and websearch query in [WEBSEARCH_QUERY_START]/[WEBSEARCH_QUERY_END]. "
                f"Your whole response should look like: '[WEBSEARCH_VALUE_START]Insert TRUE if websearch needed, FALSE if not[WEBSEARCH_VALUE_END][WEBSEARCH_QUERY_START]Insert actual websearch query here[WEBSEARCH_QUERY_END]'. Here is some conversation history in case you need more info than present in the current user input to make a query: conversation history (DO NOT EVALUATE THIS PORTION FOR WEBSEARCH NECESSITY, THIS IS JUST TO HELP INFORM YOUR WEBSEARCH QUERY IF THE CURRENT USER INPUT REQUIRES A WEBSEARCH): '{short_term_memory}'."
                "THIS IS A RETRY BECAUSE YOUR FORMATTING WASS INCORRECT ON THE FIRST ATTEMPT TO FIND THE WEBSEARCH QUERY, MAKE SURE TO FOLLOW THESE INSTRUCTIONS PERFECTLY. ",
                type='helper+'
                )
        except Exception as e:
            print(f"error during should_search: {e}")
            try:
                response = await chatbot.ask(
                    f"Your job is to check to see if websearches are necessary for incoming user inputs for the chatbot Ava. Please analyze the attached user input for websearch necessity and query. The user input is part of a larger conversation, but only the current user input needs to be evaluated for websearch necessity. Your query will be used verbatim in a google search in order to gather info about the user input. Current user input for websearch analysis: '{message}'. Put TRUE or FALSE depending on if you think a websearch is necessary for you to respond to the user input more accurately. "
                    "Websearches take a long time and use a lot of tokens so use them sparingly. Never put true if the message is just a simple 'test' or 'hello' etc. You should only put TRUE if you think the user input requires info that you do not have, i.e. if the user input has a specific question about a niche subject, "
                    "or if the user input requests real time news or weather info. Not every input will need a websearch. It will usually be obvious when a websearch is needed so when in doubt put 'false'. If websearch is true, then also include a good google search query. Use conventional techniques for advanced googling to craft the best search query possible. "
                    "You should err on the side of not doing a websearch to save costs. To identify the different segments within your response please encapsulate the the websearch necessity value in [WEBSEARCH_VALUE_START]/[WEBSEARCH_VALUE_END] and websearch query in [WEBSEARCH_QUERY_START]/[WEBSEARCH_QUERY_END]. "
                    f"Your whole response should look like: '[WEBSEARCH_VALUE_START]Insert TRUE if websearch needed, FALSE if not[WEBSEARCH_VALUE_END][WEBSEARCH_QUERY_START]Insert actual websearch query here[WEBSEARCH_QUERY_END]'. "
                    "THIS IS A RETRY BECAUSE YOUR FORMATTING WASS INCORRECT ON THE FIRST ATTEMPT TO FIND THE WEBSEARCH QUERY, MAKE SURE TO FOLLOW THESE INSTRUCTIONS PERFECTLY. ",
                    type='helper+'
                    )
            except Exception as e:
                print(f"error during should_search: {e}")
        whole_memory_summary = response["message"]
        subject = find_segment(whole_memory_summary, r"\[WEBSEARCH_QUERY_START\](.*?)\[WEBSEARCH_QUERY_END\]")
    return should_search_a, subject

async def websearch(subject, chatbot: Chatbot):
    additional_context = await search_google(subject, chatbot)
    print(f"websearch info: '{additional_context}'") 
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
                print("No search results found.")
                return urls
            fetch_tasks = [get_webpage_content(item["link"], chatbot) for item in results_json["items"]]
            contents = await asyncio.gather(*fetch_tasks)
            for url, content in zip([item["link"] for item in results_json["items"]], contents):
                if content is not None:
                    print(f"url: {url} content: {content}")
                    urls.append({"url": url, "content": content})
    print("websearch completed")
    print(f"Number of searches performed: {len(urls)}")
    print(f"complete_search_results: {urls}")
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
    
async def get_chat_input(config: ConfigManager):
    #implement your own frontend for fetching inputs
    user_input = ' '
    return user_input
    
async def get_listen_input(config: ConfigManager):
    #implement your own frontend for fetching user inputs
    audio_file_path = ""
    if os.path.exists(audio_file_path):
        with open(audio_file_path, "rb") as audio_file:
            transcript = client.audio.transcriptions.create(
                model="whisper-1", 
                file=audio_file
            )
            print(f"Transcript: {transcript.text}")
            user_input = transcript.text
    else:
        user_input = "failed to transcribe audio"
    return user_input