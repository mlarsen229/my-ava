from chatbot import Chatbot
from config_module import ConfigManager
from helpers import find_segments
import traceback

async def get_tcc_context(main_user_input, chatbot: Chatbot, config: ConfigManager):
    combined_input_data = "Processing input data... None detected yet... "
    cost = 0
    if 'gpt4v' in config.plugins:
        try:
            user_image_url = "image url"
            main_user_input += f" {user_image_url} "
            combined_input_data += "Vision data received. An image of the user will always be in this vision data. If there are multiple images, the final one will always be the user. "
            url_pattern = r'\b((?:https?|ftp)://\S*[^\s.,;:?!])(?<![\.,;:?!])'
            image_link = find_segments(main_user_input, url_pattern)
            for index, link in enumerate(image_link):
                cost += 1
                vision_response_a = await chatbot.ask(link, "What is in this image?", type="main_response")
                vision_response_a_msg = vision_response_a["message"]
                if index == len(image_link) - 1:
                    vision_response_a_msg = f"IMAGE OF THE USER: {vision_response_a_msg}"
                combined_input_data += f"Vision input data: '{vision_response_a_msg}'. "
        except Exception as e:
            print(f"<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<< ERROR WHEN GETTING VISION INPUT: {e} >>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>")
            traceback.print_exc()
    return combined_input_data, cost