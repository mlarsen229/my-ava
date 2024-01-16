import os
import sys

def resource_path(relative_path):
    """ Get absolute path to resource, works for dev and for PyInstaller """
    try:
        # PyInstaller creates a temp folder and stores path in _MEIPASS
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.abspath(".")

    return os.path.join(base_path, relative_path)

GOOGLE_APPLICATION_CREDENTIALS = resource_path('credentials.json')
MP3_FOLDER = resource_path('mp3_songs')
FFMPEG_PATH = resource_path('ffmpeg.exe')
#FFMPEG_PATH = "C:/Program Files (x86)/ffmpeg-6.0-essentials_build/bin/ffmpeg.exe"
STREAMLINK_PATH = resource_path('streamlink.exe')
#STREAMLINK_PATH = "C:/Users/mlars/AppData/Local/Programs/Python/Python311/Scripts/streamlink.exe"
#SSLCERT = "C:/Users/mlars/OneDrive/Desktop/AI_playground/server/blankbot/certificate.pem"
SSLCERT = resource_path('certificate.pem')
#SSLKEY = "C:/Users/mlars/OneDrive/Desktop/AI_playground/server/blankbot/private-key.key"
SSLKEY = resource_path('private-key.key')