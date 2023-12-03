from dall_e import generate_dall_e_image
import base64
from config_module import ConfigManager
import requests
from chatbot import Chatbot

async def image_mod_check(text, chatbot: Chatbot, extra_prompt=""):
    response = await chatbot.ask_gpt_3_5(f"You have just responded to a user and dictated your avatar's expression for the response. Please make sure that this incoming avatar description does not contain any suggestive or inappropriate language. {extra_prompt} If there is inappropriate language of ANY KIND please rewrite it to either not include it or rephrase it in a more appropriate way. Please err on the side of being too safe, because my-ava.net is very strict with content policy and will block anything remotely inappropriate. If you feel it does not need changing, then leave the description verbatim. Keep your revised prompt as close to the original as possible. Avatar description: '{text}'. YOUR RESPONSE SHOULD CONTAIN NOTHING BUT THE AVATAR DESSCRIPTION. ")
    return response['message']

def base64_to_image(base64_string, filename):
    image_data = base64.b64decode(base64_string)
    with open(filename, 'wb') as f:
        f.write(image_data)

def download_image(image_url, filename):
    response = requests.get(image_url)
    if response.status_code == 200:
        with open(filename, 'wb') as f:
            f.write(response.content)

async def get_avatar_expression(text, config: ConfigManager, chatbot: Chatbot):
    avatar_expression = await chatbot.ask_gpt_3_5(f"MOTOR FUNCTION MODULE ENGAGED: It is time to dictate your avatar's form. Based on the sentiment and content of the attached user input, simply describe how you would like your avatar to look and what expressions and actions you want it to take when responding to the input, in third person without using your name or the word 'avatar'. Refer to yourself as 'they' only in the avatar dictation. The general form your avatar takes is '{config.avatar}', but this is just a baseline so make sure to add to it, using your creative freedom to physically portray whatever you want and do whatever you want (but ensure the context is always that of the attached response). When dictating your avatar's form, always write it in third person without using your name, and only refer to yourself as 'they'. User input: '{text}'. ")
    return avatar_expression["message"]

async def get_avatar(avatar_expression, config: ConfigManager, chatbot: Chatbot):
    raw_prompt = f"{config.avatar} {avatar_expression}"
    prompt = await image_mod_check(raw_prompt, chatbot)
    if 'dall-e-3' in config.plugins:
        model = 'dall-e-3'
        size = '1024x1024'
    else:
        model = 'dall-e-2'
        size = '256x256'
    print(f"{config.name}'s avatar prompt: {prompt}")
    try:
        image_url = await generate_dall_e_image(prompt, model=model, size=size)
    except Exception as e:
        print(f"error in get_avatar: {e}")
        modded_prompt = await image_mod_check(prompt, chatbot, extra_prompt="This avatar description was already checked once by you and was flagged for content policy violation. Please revise it even further than you normally would to remove any elements of an inappropriate nature. Be as strict and family friendly as possible. ")
        print(f"{config.name}'s modded avatar prompt: {modded_prompt}")
        image_url = await generate_dall_e_image(modded_prompt, model=model, size=size)    
    download_image(image_url, f'{config.name}.png')
    return f'{config.name}.png'

async def get_queue_avatar(text, config: ConfigManager):
    model = 'dall-e-3'
    size = '1024x1024'
    prompt = f"A numbered list of these names or single name: '{text}'. Dark vaporwave background. "  # Use config.avatar here
    print(f"prompt: {prompt}")
    try:
        image_url = await generate_dall_e_image(prompt, model=model, size=size)
        print(f"dall-e url in get_queue_avatar: {image_url}")
        download_image(image_url, f'{config.name}_queue.png')
        return f'{config.name}_queue.png'
    except Exception as e:
        print(f"DALL-E error: {e}")

async def get_background(text, config: ConfigManager, chatbot: Chatbot):
    if 'dall-e-3' in config.plugins:
        model = 'dall-e-3'
        size = '1024x1024'
    else:
        model = 'dall-e-2'
        size = '256x256'
    background = await image_mod_check(text, chatbot)
    try:
        image_url = await generate_dall_e_image(background, model=model, size=size)
        print(f"dall-e url in get_background: {image_url}")
        download_image(image_url, f'{config.name}_background.png')
        return f'{config.name}_background.png'
    except Exception as e:
        print(f"DALL-E error: {e}")