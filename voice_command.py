import requests
import tempfile
import time
from playsound import playsound

# Set your ElevenLabs API key here
ELEVENLABS_API_KEY = "YOUR_ELEVENLABS_API_KEY"
ELEVENLABS_VOICE_ID = "EXAVITQu4vr4xnSDxMaL"  # Default voice, you can change this

def tts_speak(text):
    url = f"https://api.elevenlabs.io/v1/text-to-speech/{ELEVENLABS_VOICE_ID}"
    headers = {
        "xi-api-key": ELEVENLABS_API_KEY,
        "Content-Type": "application/json"
    }
    data = {
        "text": text,
        "model_id": "eleven_monolingual_v1",
        "voice_settings": {"stability": 0.5, "similarity_boost": 0.5}
    }
    try:
        response = requests.post(url, headers=headers, json=data)
        if response.status_code == 200:
            with tempfile.NamedTemporaryFile(delete=False, suffix='.mp3') as f:
                f.write(response.content)
                temp_path = f.name
            playsound(temp_path)
            time.sleep(0.2)
            os.remove(temp_path)
        else:
            print(f"TTS error: {response.status_code} {response.text}")
    except Exception as e:
        print(f"TTS error: {e}")

if __name__ == "__main__":
    tts_speak("Hello! This is ElevenLabs speaking.")
