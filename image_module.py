from dall_e import generate_dall_e_image
import base64
from config_module import ConfigManager
import requests
from chatbot import Chatbot
from sd_module import animate
from PIL import Image, ImageSequence
from helpers import convert_to_gif_format

async def loop_gif(input_path, output_path="loopedgif.gif"):
    with Image.open(input_path) as img:
        frames = [frame.copy() for frame in ImageSequence.Iterator(img)]
        reversed_frames = frames[::-1]
        boomerang_frames = frames + reversed_frames[1:-1]
        boomerang_frames[0].save(output_path, save_all=True, append_images=boomerang_frames[1:], loop=0, duration=img.info['duration'])
        return output_path

async def image_mod_check(text, chatbot: Chatbot, extra_prompt=""):
    image_link = None
    prompt = (
        f"You are a moderation bot for subprocesses in my-ava.net's software. Please make sure that this incoming text chunk does not contain any suggestive or inappropriate language. {extra_prompt} "
        "If there is inappropriate language of ANY KIND please rewrite it to either not include it or rephrase it in a more appropriate way. "
        "Please err on the side of being too safe, because my-ava.net is very strict with content policy and will block anything remotely inappropriate. "
        "If you feel it does not need changing, then leave the text chunk verbatim. Keep your revised text chunk as close to the original as possible. "
        f"TEXT CHUNK: '{text}'. YOUR RESPONSE SHOULD CONTAIN NOTHING BUT THE REVISED TEXT CHUNK. "
    )
    response = await chatbot.ask(image_link, prompt, type='helper')
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
    image_link = None
    prompt = (
        f"MOTOR FUNCTION MODULE ENGAGED: It is time to dictate your avatar's form via a brief description of your avatar in your response. "
        "Based on the sentiment and content of your attached response, simply describe how you would like your avatar to look and what expressions and actions you want it to take during this response, "
        "in third person without using your name or the word 'avatar'. Refer to yourself as 'they' only in the avatar dictation. "
        f"The general form your avatar takes is '{config.avatar}', but this is just a baseline so make sure to add to it, using your creative freedom to physically portray whatever you want and do whatever you want "
        "(but ensure the context is always that of the attached response). When dictating your avatar's form, always write it in third person without using your name, and only refer to yourself as 'they'. "
        f"YOUR RESPONSE SHOULD CONTAIN NOTHING BUT YOUR AVATAR DICATION. Your response: '{text}'. "
    )
    avatar_expression = await chatbot.ask(image_link, prompt, type='helper+')
    return avatar_expression["message"]

async def get_anim_avatar_expr(text, config: ConfigManager, chatbot: Chatbot):
    image_link = None
    extra_anim_instr = (
        "You have a moving avatar, so you can dictate its movement bit by bit, frame by frame. "
        "Please respond with your avatar's action/movement description nested incrementally within [FRAME_X_START] and [FRAME_X_END] for identification within subprocesses. "
        "For example, a response might read: '[FRAME_1_START] They are starting to do something. [FRAME_1_END] [FRAME_2_START] They are doing slightly more. [FRAME_2_END] "
        "[FRAME_3_START] They are about halfway through the action. [FRAME_3_END] [FRAME_4_START] They are slightly further along in the action. [FRAME_4_END] "
        "[FRAME_5_START] They are almost done with the whole movement/action. [FRAME_5_END] [FRAME_6_START] They are done moving. [FRAME_6_END]'. "
        "Make sure the frames are not too different or drastic of movements, each one should be small and incremental, meant to describe a small part of one large overarching action. ALWAYS REMEMBER ALL 6 FRAMES. "
    )
    avatar_expression = await chatbot.ask(image_link, f"MOTOR FUNCTION MODULE ENGAGED: It is time to dictate your avatar's form via a brief description of your avatar in your response. Based on the sentiment and content of your attached response, simply describe how you would like your avatar to look and what expressions and actions you want it to take during this response, in third person without using your name or the word 'avatar'. Refer to yourself as 'they' only in the avatar dictation. The general form your avatar takes is '{config.avatar}', but this is just a baseline so make sure to add to it, using your creative freedom to physically portray whatever you want and do whatever you want (but ensure the context is always that of the attached response). When dictating your avatar's form, always write it in third person without using your name, and only refer to yourself as 'they'. {extra_anim_instr} YOUR RESPONSE SHOULD CONTAIN NOTHING BUT YOUR AVATAR DICATION. Your response: '{text}'. ", type='helper+')
    avatar_expr_a = avatar_expression["message"]
    return avatar_expr_a

async def get_avatar(avatar_expression, config: ConfigManager, chatbot: Chatbot):
    if 'anim_avatar' in config.plugins:
        prompt = avatar_expression
        if 'hq_avatar' in config.plugins:
            model = "stable-diffusion-xl-1024-v0-9"
        else:
            model = "stable-diffusion-512-v2-1"
        seed = int(config.avatar_seed)
        await animate(model, 'avatar', prompt, config.name, seed)
        gif = f"{config.name}avatar.gif"
        looped_gif = await loop_gif(gif)
        return looped_gif
    else:
        raw_prompt = f"{config.avatar} {avatar_expression}"
        try:
            prompt = await image_mod_check(raw_prompt, chatbot)
        except:
            prompt = config.avatar
        if 'My-AVA is currently experiencing an outage. Please try again later.' in prompt:
            prompt = config.avatar
        if 'hq_avatar' in config.plugins:
            model = 'dall-e-3'
            size = '1024x1024'
        else:
            model = 'dall-e-2'
            size = '256x256'
        try:
            image_url = await generate_dall_e_image(prompt, model=model, size=size)
        except Exception as e:
            print(f"error in get_avatar: {e}")
            modded_prompt = await image_mod_check(prompt, chatbot, extra_prompt="This avatar description was already checked once by you and was flagged for content policy violation. Please revise it even further than you normally would to remove any elements of an inappropriate nature. Be as strict and family friendly as possible. ")
            image_url = await generate_dall_e_image(modded_prompt, model=model, size=size)    
        download_image(image_url, f'{config.name}.png')
        final_gif = convert_to_gif_format(f'{config.name}.png')
        return final_gif

async def get_queue_avatar(text, config: ConfigManager):
    model = 'dall-e-3'
    size = '1024x1024'
    prompt = f"A numbered list of these names or single name: '{text}'. Dark vaporwave background. "  # Use config.avatar here
    #print(f"prompt: {prompt}")
    try:
        image_url = await generate_dall_e_image(prompt, model=model, size=size)
        download_image(image_url, f'{config.name}_queue.png')
        return f'{config.name}_queue.png'
    except Exception as e:
        print(f"DALL-E error: {e}")

async def get_background(text, config: ConfigManager, chatbot: Chatbot):
    prompt = await image_mod_check(text, chatbot)
    if 'anim_background' in config.plugins:
        if 'hq_background' in config.plugins:
            model = "stable-diffusion-xl-1024-v0-9"
        else:
            model = "stable-diffusion-512-v2-1"
        seed = int(config.avatar_seed)
        await animate(model, 'background', prompt, config.name, seed)
        gif = f"{config.name}background.gif"
        looped_gif = await loop_gif(gif)
        return looped_gif
    else:
        if 'hq_background' in config.plugins:
            model = 'dall-e-3'
            size = '1024x1024'
        else:
            model = 'dall-e-2'
            size = '256x256'
        try:
            image_url = await generate_dall_e_image(prompt, model=model, size=size)
        except Exception as e:
            print(f"error in get_static_background: {e}")
            modded_prompt = await image_mod_check(prompt, chatbot, extra_prompt="This background description was already checked once by you and was flagged for content policy violation. Please revise it even further than you normally would to remove any elements of an inappropriate nature. Be as strict and family friendly as possible. ")
            image_url = await generate_dall_e_image(modded_prompt, model=model, size=size)    
        download_image(image_url, f'{config.name}.png')
        final_gif = convert_to_gif_format(f'{config.name}.png')
        return final_gif