import os
import time
import speech_recognition as sr
from google import genai
import pyttsx3

# You can swap pyttsx3 for another TTS library if you prefer (e.g., edge-tts, elevenlabs, etc.)

def listen_for_context():
    recognizer = sr.Recognizer()
    mic = sr.Microphone()
    print("Please describe the current app or screen you are using. Speak now...")
    with mic as source:
        recognizer.adjust_for_ambient_noise(source)
        audio = recognizer.listen(source)
    try:
        text = recognizer.recognize_google(audio)
        print(f"You said: {text}")
        return text
    except Exception as e:
        print(f"Could not understand audio: {e}")
        return None

def ask_gemini_contextual_help(context_description):
    client = genai.Client(api_key="AIzaSyB35N83uAdd5cjwfXqkLH9T9_PhWHTMSb8")
    prompt = f"A user with accessibility needs is currently using the following app or screen: {context_description}. Please provide a simple, step-by-step explanation of what they can do on this screen, and how to use it effectively. Focus on accessibility tips and easy-to-understand instructions."
    response = client.models.generate_content(
        model='gemini-2.0-flash',
        contents=prompt
    )
    return response.text

def speak_text(text):
    engine = pyttsx3.init()
    engine.setProperty('rate', 170)  # Adjust rate for clarity
    engine.say(text)
    engine.runAndWait()

def main():
    context = listen_for_context()
    if not context:
        print("No context provided. Exiting.")
        return
    answer = ask_gemini_contextual_help(context)
    print("\nGemini Accessibility Help:\n")
    print(answer)
    print("\nReading aloud...")
    speak_text(answer)

if __name__ == "__main__":
    main()
