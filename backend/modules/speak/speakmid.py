import os
import pygame
from functools import lru_cache
import random
# Removed lru_cache because caching TTS prevents repeating the same phrase
def mid(text, func=None):
    from dotenv import load_dotenv
    load_dotenv()
    elevenlabs_key = os.getenv("ELEVENLABS_API_KEY")
    
    # Safe text formatting for command line
    safe_text = str(text).replace('"', '\\"')
    
    if elevenlabs_key:
        import requests
        print("Using ElevenLabs TTS...")
        voice_id = "tS45q0QcrDHqHoaWdCDR" # Lax (Voz lendária solicitada pelo usuário)
        url = f"https://api.elevenlabs.io/v1/text-to-speech/{voice_id}"
        headers = {
            "Accept": "audio/mpeg",
            "Content-Type": "application/json",
            "xi-api-key": elevenlabs_key
        }
        data = {
            "text": text,
            "model_id": "eleven_multilingual_v3",
            "language_code": "pt",
            "voice_settings": {"stability": 0.5, "similarity_boost": 0.5}
        }
        try:
            response = requests.post(url, json=data, headers=headers)
            if response.status_code == 200:
                with open("data.mp3", "wb") as f:
                    f.write(response.content)
            else:
                raise Exception(f"ElevenLabs failed: {response.text}")
        except Exception as e:
            print(e)
            command = f'edge-tts --voice "pt-BR-AntonioNeural" --pitch=+0Hz --rate=+10% --text "{safe_text}" --write-media "data.mp3"'
            os.system(command)
    else:
        command = f'edge-tts --voice "pt-BR-AntonioNeural" --pitch=+0Hz --rate=+10% --text "{safe_text}" --write-media "data.mp3"'
        os.system(command)

    pygame.init()
    pygame.mixer.init()
    pygame.mixer.music.load("data.mp3")
    try:
        pygame.mixer.music.play()
        while pygame.mixer.music.get_busy():
            pygame.time.Clock().tick(10)
    except Exception as e:
        print(e)
    finally:
        pygame.mixer.music.stop()
        pygame.mixer.quit()

def TTS(Text, func=lambda r=None: True):
    Data = str(Text).split('.')
    responses = ['The rest of the result has been printed to the chat screen, kindly check it out sir.The rest of the text is now on the chat screen, sir, please check it.', 'You can see the rest of the text on the chat screen, sir.', 'The remaining part of the text is now on the chat screen, sir.', "Sir, you'll find more text on the chat screen for you to see.", 'The rest of the answer is now on the chat screen, sir.', 'Sir, please look at the chat screen, the rest of the answer is there.', "You'll find the complete answer on the chat screen, sir.", 'The next part of the text is on the chat screen, sir.', 'Sir, please check the chat screen for more information.', "There's more text on the chat screen for you, sir.", 'Sir, take a look at the chat screen for additional text.', "You'll find more to read on the chat screen, sir.", 'Sir, check the chat screen for the rest of the text.', 'The chat screen has the rest of the text, sir.', "There's more to see on the chat screen, sir, please look.", 'Sir, the chat screen holds the continuation of the text.', "You'll find the complete answer on the chat screen, kindly check it out sir.", 'Please review the chat screen for the rest of the text, sir.', 'Sir, look at the chat screen for the complete answer.']
    if len(Data) > 4 and len(Text) >= 250:
        mid(' '.join(Text.split('.')[0:2]) + '. ' + random.choice(responses), func)
    else:
        mid(Text, func)

if __name__ == '__main__':
    while True:
        TTS(input('Enter the text : '))