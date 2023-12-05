from bot_module import StandardBot

async def send_text_input(bot: StandardBot, user_input):
    bot_response, avatar = await bot.handle_chat_command(user_input)
    return bot_response, avatar