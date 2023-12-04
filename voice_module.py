from google.cloud import texttospeech
import uuid
from google.oauth2.service_account import Credentials
from dotenv import load_dotenv
import os

load_dotenv()
GOOGLE_APPLICATION_CREDENTIALS = os.getenv("GOOGLE_APPLICATION_CREDENTIALS")

def tts_to_audio_file(text, config_voice, language_code='', file_format='mp3'):
    #look for US or GB in config_voice and assign language_code accordingly
    config_voice_upper = config_voice.upper()
    if 'US' in config_voice_upper:
        language_code = 'en-US'
    elif 'GB' in config_voice_upper:
        language_code = 'en-GB'
    elif 'AU' in config_voice_upper:
        language_code = 'en-AU'
    else:
        raise ValueError(f'Unsupported language code in config_voice: {config_voice}')
    print(f"Using language code: {language_code}")
    credentials = Credentials.from_service_account_file(GOOGLE_APPLICATION_CREDENTIALS)
    client = texttospeech.TextToSpeechClient(credentials=credentials)
    print(f"Using voice: {config_voice}")
    ssml_text = f'<speak>{text}</speak>'
    input_text = texttospeech.SynthesisInput(ssml=ssml_text)

    voice = texttospeech.VoiceSelectionParams(
        language_code=language_code,
        name=f'{config_voice}'
    )

    audio_config = texttospeech.AudioConfig(
        audio_encoding=get_audio_encoding(file_format)
    )

    response = client.synthesize_speech(
        input=input_text,
        voice=voice,
        audio_config=audio_config
    )

    # Generate a unique filename for each operation
    file_name = f"output_{uuid.uuid4()}.{file_format}"

    with open(file_name, 'wb') as out:
        out.write(response.audio_content)

    return file_name

def get_audio_encoding(file_format):
    if file_format.lower() == 'mp3':
        return texttospeech.AudioEncoding.MP3
    elif file_format.lower() == 'wav':
        return texttospeech.AudioEncoding.LINEAR16
    elif file_format.lower() == 'ogg':
        return texttospeech.AudioEncoding.OGG_OPUS
    else:
        raise ValueError('Unsupported file format')