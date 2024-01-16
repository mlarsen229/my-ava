import logging
from chatbot import Chatbot
from helpers import find_segment, should_search, websearch, truncate_backwards, Memory
from config_module import ConfigManager
from twitchio import Channel
from msg_out import send_text_response
import uuid
import traceback
from dall_e import generate_dall_e_image
from sd_module import animate
from image_module import download_image, loop_gif

logging.basicConfig(level=logging.INFO)

async def make_file(filename, content, dall_e_model, dall_e_size, sd_model, anim_type):
    text_extensions = ['.txt', '.py', '.js', '.html', '.css', '.cfg', '.conf', '.xml']
    image_extensions = ['.jpg', '.png']
    anim_extensions = ['.gif']
    if any(filename.endswith(ext) for ext in text_extensions):
        with open(filename, 'w') as file:
            file.write(content)
    elif any(filename.endswith(ext) for ext in image_extensions):
        image_url = await generate_dall_e_image(content, 1, dall_e_size, dall_e_model)
        download_image(image_url, filename)
    elif any(filename.endswith(ext) for ext in anim_extensions):
        animation_path = await animate(sd_model, anim_type, content, output_name=filename)
        looped_animation = await loop_gif(animation_path, filename)
        filename = looped_animation
    return filename

async def get_brainstorm_procedure(general_prompt, user_input, bot_response, chatbot: Chatbot, memory: Memory, config: ConfigManager):
    if 'autonomy' in config.plugins:
        additional_prompt = "YOU HAVE EXTENDED AUTONOMY. YOU CAN USE MULTIPLE STEPS/RESPONSES TO FINISH THE USER'S TASK. "
    else:
        additional_prompt = "YOU DO NOT HAVE EXTENDED AUTONOMY. YOU MUST CRAFT YOUR PROCEDURE SUCH THAT YOU CAN FINISH THE USER'S TASK IN ONE SINGLE STEP. WHATEVER THE REQUEST, IT MUST BE DONE IN ONE STEP. "
    prompt = (
        f"{general_prompt} {additional_prompt} You have just responded to a user. Please review this user input and your response to it and determine whether any research/autonomous work is necessary to fully complete the user request. "
        "If your response says that you will do some autonomous work, then do so. You will have already formed your main response to the user input, you just need to do followup work now. "
        "This includes things like large language-based projects, extensive reviews of data, formation of meta-level conclusions, etc. However, this does not include queue creation/maintennance and background creation. "
        "You do not need to do autonomous work unless specifically asked to or you are asked to for create of a file (image, animation, OR text-based files) or it is a more complicated, large-scale project. You are able to do any of these types of tasks thanks to your autonomy module. "
        "To get started with the process, simply begin your response with '[WORK_VALUE_START] TRUE [WORK_VALUE_END]' or '[WORK_VALUE_START] FALSE [WORK_VALUE_END]' depending on if brainstorming/research/preparation via autonomous work is necessary or not. "
        "Remember, this should always be false in the case of background or queue creation/maintennance. If it is true, also describe for the user in GREAT detail the procedure you need to follow to complete whatever the user tasked you with including general concepts and specific actions like file creation (you can create image files and text-based files) and response message formation, enclosed in '[PROCEDURE_START] (your procedure here) [PROCEDURE_END]'. "
        "Think stepwise and determine how you specifically can complete the task as a language-based entity with real-time websearch capabilities. If work value is true, your response should look like [WORK_VALUE_START] TRUE [WORK_VALUE_END] [PROCEDURE_START] This is where the procedure goes [PROCEDURE_END]. "
        "If files/images/animations are requested, the only instruction needed is 'create x filetype with x file contents'. No additional instructions for preparation or uploading files etc is necessary, it is all taken care of automatically without need for action from you. "
        "UNDER NO CIRCUMSTANCES SHOULD YOU INCLUDE INSTRUCTIONS FOR UPLOADING FILES TO THE CLOUD BUCKET IN YOUR PROCEDURE. SIMPLY SAY 'CREATE FILE WITH XYZ'. "
        f"ALWAYS INCLUDE THESE IDENTIFYING TAGS EXACTLY AS THEY APPEAR. Your response should include nothing but the work value and the procedure if applicable. User input: '{user_input}'. Your response to the user input: '{bot_response}'. "
    )
    intro_response = await chatbot.ask(None, prompt, type="helper+")
    intro_response_msg = intro_response["message"]
    brainstorm_value = find_segment(intro_response_msg, r"\[WORK_VALUE_START\](.*?)\[WORK_VALUE_END\]")
    if "TRUE" in brainstorm_value.upper():
        brainstorm_value = True
        brainstorm_procedure = find_segment(intro_response_msg, r"\[PROCEDURE_START\](.*?)\[PROCEDURE_END\]")
    else:
        brainstorm_value = False
        brainstorm_procedure = "No brainstorming necessary"
    return brainstorm_value, brainstorm_procedure

async def get_brainstorm_followup(procedure, last_response, general_prompt, user_input, chatbot: Chatbot, memory: Memory, config: ConfigManager):
    try:
        if 'autonomy' in config.plugins:
            additional_prompt = "YOU HAVE EXTENDED AUTONOMY. YOU CAN USE MULTIPLE STEPS/RESPONSES TO FINISH THE USER'S TASK. "
        else:
            additional_prompt = "YOU DO NOT HAVE EXTENDED AUTONOMY. YOU MUST FINISH THE USER'S TASK IN THIS ONE SINGLE STEP. IF YOU WERE TASKED WITH CREATING AN IMAGE/ANIMATION/FILE YOU MUST DO SO NOW. EVEN THOUGH YOU DO NOT HAVE EXTENDED AUTONOMY YOU CAN STILL MAKE IMAGES AND ANIMATIONS AND SINGLE TEXT-BASED FILES. "
        file_type = " "
        file_contents = " "
        websearch_context = ' '
        auto_cost = 0
        cost_value = 0
        img_cost_value = 1
        websearch_text = f"YOU ARE CURRENTLY IN THE PROCESS OF COMPLETING THIS PROCEDURE: '{procedure}'. YOU ARE ON THIS STEP: '{last_response}'. "
        should_search_value, subject = await should_search(websearch_text, chatbot, memory)
        if 'hd_images' in config.plugins:
            dall_e_model = 'dall-e-3'
            dall_e_size = '1024x1024'
            sd_model = 'stable-diffusion-xl-1024-v0-9'
            img_cost_value += 2
        else:
            dall_e_model = 'dall-e-2'
            dall_e_size = '256x256'
            sd_model = 'stable-diffusion-512-v2-1'
        if "true" in should_search_value.lower():
            websearch_query = subject
        else:
            websearch_query = None
        if websearch_query is not None:
            try:
                raw_websearch_context = await websearch(websearch_query, chatbot)
                websearch_context_a = ' '.join([f"{item['url']}: {item['content']}" for item in raw_websearch_context if isinstance(item, dict)])
                websearch_context = f"Here is some websearch data to help you form your response: '{websearch_context_a}'. "
            except Exception as e:
                logging.error(f"<<<<<<<<<<<<<<<<<<<<<<<<<< ERROR DURING WEBSEARCH IN AUTONOMY MODULE: {e} >>>>>>>>>>>>>>>>>>>>>>>")
                websearch_context = "Websearch unsuccessful. "
        followup_prompt = (
            f"{general_prompt} You are following up to one of your past responses in the autonomous work process. {additional_prompt} "
            f"This is the user input you are tasked with solving: '{user_input}'. This is the procedure you are following to solve said task: '{procedure}'. "
            f"This was your last response that you are following up to: '{last_response}'. Proceed with the next step. Do so by carrying out the action described in the procedure to the best of your ability. "
            "Publish your results in file output form if applicable with a breakdown of the results in your main response message body. "
            "In your response message, always include a full unlabeled breakdown of your results in the form of a short paragraph, in addition to all other labeled parts of the response message. "
            "You have the ability to dictate the creation of text-based AND image files (including gifs for animations), so if you need to make a text-based file (.txt, .json, .html, .py, etc) or an image file (.png, .jpg, .gif) as part of this procedural step, do so by writing '[MAKEFILE_VALUE_START] (TRUE or FALSE) [MAKEFILE_VALUE_END]' "
            "then if it is 'TRUE', write '[FILE_TYPE_START] .txt or .png or .gif (or other desired type) [FILE_TYPE_END] [FILE_CONTENT_START] insert contents here or image/animation description here [FILE_CONTENT_END]' within your response (in addition to the rest of the response message). When making image files, the file content section should be a vivid and detailed description of what the image should look like. "
            "Treat images and animations the exact same as text files. Use the same format for dictating/labeling images and animations as you would a text file. When dictating the contents of the images and animations, you need only describe the image or animation with no extra comments or decorators. E.g. if you want to create an image/animation of a fish swimming in the ocean, you would respond '[FILE_CONTENT_START] A fish swimming in the ocean. [FILE_CONTENT_END]'. "
            "Files you create will automatically be uploaded to a secure google cloud bucket for the user to access. If you create a file during the autonomous work process, do not add any extra labels or identifiers to the URL of the file. "
            "Make sure that you follow this format exactly with these identifying tags for subprocesses: '[MAKEFILE_VALUE_START] insert_value_here [MAKEFILE_VALUE_END] [FILE_TYPE_START] insert_filetype_here [FILE_TYPE_END] [FILE_CONTENT_START] insert_file_content_here [FILE_CONTENT_END] [FOLLOWUP_MESSAGE_START] rest_of_response_message [FOLLOWUP_MESSAGE_END]'. "
            "Do not include any make file info or directives if you do not feel you need to make a file. ACTUALLY PERFORM THE SPECIFIC ACTION, DO NOT SIMPLY SAY THAT YOU HAVE COMPLETED IT. "
            "GO INTO GREAT LENGTH TO COMPILE DATA AND WORK THROUGH THE STEP IN THE PROCEDURE. ALWAYS INCLUDE THE RESULTS OF THIS STEP OF THE PROCEDURE. Always clearly explain your logic and train of thought. "
            "ALWAYS INCLUDE GATHERED DATA IN YOUR RESPONSE MESSAGE, YOUR RESPONSE WILL BE USED IN A FOLLOWUP SO MAKE SURE RELEVANT DATA IS ALWAYS INCLUDED IN YOUR RESPONSE. "
            "If, when you are finished with this step, you have sufficiently completed the task given to you, or if you can no longer make any progress on said task, respond with FALSE for the followup value (always return the results of your work even if the followup value is false). "
            "If you can keep going and you need to keep going with the next step, put TRUE for the followup value. Always 'show your work' and include all relevant info and data you've gathered to complete said task. "
            "Always end your response with a followup value enclosed in '[FOLLOWUP_VALUE_START] TRUE/FALSE [FOLLOWUP_VALUE_END]'. "
            "Your whole response should look like: '[MAKEFILE_VALUE_START] insert_value_here [MAKEFILE_VALUE_END] [FILE_TYPE_START] insert_filetype_here_if_makefile_value_true [FILE_TYPE_END] [FILE_CONTENT_START] insert_file_content_here_if_makefile_value_true [FILE_CONTENT_END] [FOLLOWUP_MESSAGE_START] rest_of_response_message [FOLLOWUP_MESSAGE_END] [FOLLOWUP_VALUE_START] insert_followup_value_here [FOLLOWUP_VALUE_END]'. "
            f"The followup message section of your response message should always contain a comprehensive review of all the work you have done so far. Some relevant websearch info for your use in forming a response: '{websearch_context}'. "
        )
        followup_response = await chatbot.ask(None, followup_prompt, type="helper+")
        followup_response_msg = followup_response["message"]
        followup_value = find_segment(followup_response_msg, r"\[FOLLOWUP_VALUE_START\](.*?)\[FOLLOWUP_VALUE_END\]")
        makefile_value = find_segment(followup_response_msg, r"\[MAKEFILE_VALUE_START\](.*?)\[MAKEFILE_VALUE_END\]")
        followup_message = find_segment(followup_response_msg, r"\[FOLLOWUP_MESSAGE_START\](.*?)\[FOLLOWUP_MESSAGE_END\]")
        if 'TRUE' in makefile_value.upper():
            try:
                cost_value += 1
                makefile_value = True
                file_type_a = find_segment(followup_response_msg, r"\[FILE_TYPE_START\](.*?)\[FILE_TYPE_END\]")
                file_type = file_type_a.replace(" ", "")
                if file_type.endswith('.jpg'):
                    cost_value += 1
                    cost_value += img_cost_value
                elif file_type.endswith('.png'):
                    cost_value += 1
                    cost_value += img_cost_value
                elif file_type.endswith('.gif'):
                    cost_value += 3
                    cost_value += img_cost_value
                file_contents = find_segment(followup_response_msg, r"\[FILE_CONTENT_START\](.*?)\[FILE_CONTENT_END\]")
                unique_id = str(uuid.uuid4())
                name = f"{unique_id}{file_type}"
                file_path = await make_file(name, file_contents, dall_e_model, dall_e_size, sd_model, 'standard')
                followup_message += file_path
                auto_cost += cost_value
            except Exception as e:
                logging.error(f"<<<<<<<<<<<<<<<<<<<<<<< ERROR IN GETTING FILE URL: {e} >>>>>>>>>>>>>>>>>>>>>>>>>>>>>>> ")
                traceback.print_exc()
        else:
            makefile_value = False
        if "TRUE" in followup_value.upper():
            followup_value = True
        else:
            followup_value = False
    except Exception as e:
        logging.error(f"<<<<<<<<<<<<<<<<<<<<<<<< ERROR IN GET_BRAINSTORM_FOLLOWUP: {e} >>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>")
        followup_value = False
        followup_message = f"An error occured during the autonomous work process: '{e}'. "
        auto_cost = 2
    return followup_value, followup_message, auto_cost

async def brainstorm(response_platform, user_input, bot_response, chatbot: Chatbot, memory: Memory, config: ConfigManager, twitch_channel: Channel, discord_channel):
    cost = 0
    general_prompt = (
        "AUTONOMY MODULE ENGAGED: You are within a subprocess after main response formation in which you will undergo a process of first evaluating a user input for 'autonomous work' necessity. "
        "'Autonomous work' just means you are completing a task by yourself programmatically without further input from the user. There are two kinds of autonomous work: file creation and response message formation. "
        "While autonomously working, you may be asked to create files, form response messages, or both. The process works as follows: First you will identify the task that requires autonomous work, then you will create a stepwise procedure to complete the task. "
        "The type of task will vary, but in every case you should use the procedure to tell yourself how to complete the task via creating files, and writing response messages. After creating a procedure you will automatically be prompted to go through each step. "
        "The types of files you can create are image files (.png and .jpg), animations (.gif), and text-based files (.txt, .py, .js, .html, .css, .conf, .cfg, .xml, etc). To create files all you have to do is dictate the file contents in one short response. "
    )
    value, procedure = await get_brainstorm_procedure(general_prompt, user_input, bot_response, chatbot, memory, config)
    if value == False:
        return procedure, cost
    if 'autonomy' in config.plugins:
        await send_text_response(response_platform, f"{procedure} Please be patient while I work on this request. ", config, twitch_channel, discord_channel)
    last_response = " "
    value = True
    followup_count = 0
    while value == True:
        value, followup, auto_cost = await get_brainstorm_followup(procedure, last_response, general_prompt, user_input, chatbot, memory, config)
        cost += auto_cost
        last_response += followup
        if len(last_response) > 8000:
            truncated_text = truncate_backwards(last_response, 6000)
            last_response = truncated_text
        followup_count += 1
        if followup_count > 3:
            last_response += f"Autonomous work exceeded 3 followup responses. Do the best with the gathered info. "
            break
    return last_response, cost