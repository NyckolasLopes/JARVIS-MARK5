import json
import threading
import os
import mtranslate as mt
from threading import Lock
import os
import eel
import pyautogui

import base64
from backend.modules.extra import LoadMessages
from dotenv import load_dotenv

def get_api():
    try:
      
        with open('config/config.json') as config_file:
            config = json.load(config_file)
            API = config.get('GROQ_API')
            if API is None:
                raise ValueError("GROQ_API URL not found in config file")
            return API
    except FileNotFoundError:
        print("Config file not found.")
    except json.JSONDecodeError:
        print("Error decoding JSON in config file.")
    except Exception as e:
        print(f"Error reading config file: {e}")
    return None

os.environ['GROQ_API'] = get_api()

from backend.modules.automodel import Operate, speak
from backend.modules.basic.listenpy import Listen

def run_docker():
    import os
    os.chdir("backend/AI/Perplexica")
    os.system("docker compose up -d")

thread = threading.Thread(target=run_docker)
thread.start()

load_dotenv()
state = 'Available...'
messages = LoadMessages()
WEBCAM = False
js_messageslist = []
working: list[threading.Thread] = []
InputLanguage = os.environ['InputLanguage']
Username = os.environ['NickName']
lock = Lock()

def UniversalTranslator(Text: str) -> str:
    """Translates text to English."""
    english_translation = mt.translate(Text, 'en', 'auto')
    return english_translation.capitalize()

def MainExecution(Query: str):
    """Main execution function for handling user queries."""
    global WEBCAM, state
    Query = UniversalTranslator(Query) if 'en' not in InputLanguage.lower() else Query.capitalize()

    if state not in ['Available...', 'Listening...']:
        return
        
    # Sistema de Wake Word
    clean_query = Query.lower().strip(' .?!,')
    if clean_query == "jarvis":
        speak("Como posso te ajudar, Nyckolas?")
        state = 'Available...'
        return "wake_word_acknowledged"
        
    state = 'Thinking...'
    Decision = Operate(Query)

    if Decision and 'realtime-webcam' in Decision:
        python_call_to_start_video()
        print('Video Started')
        WEBCAM = True
    elif Decision and 'close_webcam' in Decision:
        print('Video Stopped')
        python_call_to_stop_video()
        WEBCAM = False
        
    state = 'Available...'
    return Decision

@eel.expose
def js_messages():
    """Fetches new messages to update the GUI."""
    global messages, js_messageslist
    with lock:
        messages = LoadMessages()
    if js_messageslist != messages:
        js_messageslist = messages.copy()
        return messages
    return messages

@eel.expose
def js_state(stat=None):
    """Updates or retrieves the current state."""
    global state
    if stat:
        state = stat
    return state

def process_input(transcription):
    global WEBCAM
    result = MainExecution(transcription)
    if result == "close_webcam":
        print('Video Stopped')
        python_call_to_stop_video()
        WEBCAM = False

def main_listening_loop():
    """Background loop that uses Python speech_recognition to listen."""
    global state
    
    # Saudação inicial solicitada pelo usuário
    state = 'Thinking...'
    speak("Bem vindo senhor.")
    import time
    time.sleep(0.5)
    speak("Um momento enquanto eu me conecto a nossa central.")
    speak("Estou pronto, o que precisa?")
    
    state = 'Available...'
    
    while True:
        if state == 'Available...':
            state = 'Listening...'
            
            transcription = Listen()
            
            if transcription:
                # Run process in a separate thread so listening loop can reset after
                t = threading.Thread(target=process_input, args=(transcription,), daemon=True)
                t.start()
                t.join() # Wait for processing to finish before listening again
            else:
                state = 'Available...'

@eel.expose
def frontend_ready():
    """Triggered by JS when the UI overlay is clicked, starting the Python listening loop."""
    print("Frontend ready. Starting Python listening loop...")
    threading.Thread(target=main_listening_loop, daemon=True).start()

@eel.expose
def python_call_to_start_video():
    """Starts the video capture."""
    eel.startVideo()

@eel.expose
def python_call_to_stop_video():
    """Stops the video capture."""
    eel.stopVideo()

@eel.expose
def python_call_to_capture():
    """Captures an image from the video."""
    eel.capture()

@eel.expose
def handle_captured_image(image_data):
    """Handles the captured image data from the web interface."""
    js_capture(image_data)

@eel.expose
def js_page(cpage=None):
    """Navigates to the specified page."""
    if cpage == 'home':
        eel.openHome()
    elif cpage == 'settings':
        eel.openSettings()

@eel.expose
def setup():
    """Sets up the GUI window."""
    pyautogui.hotkey('win', 'up')

@eel.expose
def js_language():
    """Returns the input language."""
    return str(InputLanguage)

@eel.expose
def js_assistantname():
    """Returns the assistant's name."""
    return "JARVIS"

@eel.expose
def js_capture(image_data):
    """Saves the captured image."""
    image_bytes = base64.b64decode(image_data.split(',')[1])
    with open('capture.png', 'wb') as f:
        f.write(image_bytes)

current_dir = os.path.dirname(os.path.abspath(__file__))
web_dir = os.path.join(current_dir, 'web')
eel.init(web_dir)
eel.start('spider.html', port=44444)