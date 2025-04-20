import pyaudio
import wave
import requests
import json
import tempfile
import time
import os
import numpy as np
from pydub import AudioSegment
from pydub.silence import split_on_silence
from dotenv import load_dotenv
import speech_recognition as sr
import threading
import queue
from elevenlabs import ElevenLabs

# Load environment variables from .env file
load_dotenv()

# Audio recording parameters
CHUNK = 1024
FORMAT = pyaudio.paInt16
CHANNELS = 1
RATE = 16000
WAKE_WORD = "Hey Aggie"
client = ElevenLabs(
  api_key=os.getenv("ELEVENLABS_KEY")
)

class WakeWordDetector:
    def __init__(self):
        self.audio_queue = queue.Queue()
        self.recognizer = sr.Recognizer()
        self.recognizer.energy_threshold = 1000  # Adjust based on your environment
        self.recognizer.dynamic_energy_threshold = True
        self.listening = False
        self.wake_word_detected = False
        self.p = pyaudio.PyAudio()
        self.stream = None

        
    def transcribe_with_elevenlabs(self, audio_file):
      """Transcribe audio file using ElevenLabs API."""
      
      audio_data = open(audio_file, 'rb').read()
      
      transcription = client.speech_to_text.convert(
        file=audio_data,
        model_id="scribe_v1", # Model to use, for now only "scribe_v1" is supported
        tag_audio_events=True, # Tag audio events like laughter, applause, etc.
        language_code="eng", # Language of the audio file. If set to None, the model will detect the language automatically.
        diarize=True, # Whether to annotate who is speaking
      )
      print(transcription.text)
      with open("transcription.txt", "w") as file:
          file.write(transcription.text)
          
      return transcription.text
        
    def start_listening(self):
        """Start listening for audio in the background."""
        self.listening = True
        self.stream = self.p.open(
            format=FORMAT,
            channels=CHANNELS,
            rate=RATE,
            input=True,
            frames_per_buffer=CHUNK,
            stream_callback=self._audio_callback
        )
        self.stream.start_stream()
        
    def _audio_callback(self, in_data, frame_count, time_info, status):
        """Callback for audio stream, puts audio data in queue."""
        self.audio_queue.put(in_data)
        return (in_data, pyaudio.paContinue)
    
    def stop_listening(self):
        """Stop listening for audio."""
        if self.stream:
            self.stream.stop_stream()
            self.stream.close()
        self.listening = False
        self.p.terminate()
    
    def detect_wake_word(self):
        """Continuously process audio to detect wake word."""
        print("Listening for 'Hey Aggie'...")
        
        # Buffer to accumulate audio data
        audio_buffer = []
        buffer_max_size = int(RATE / CHUNK * 3)  # 5 seconds of audio
        while self.listening:
            try:
                # Get audio data from queue
                audio_data = self.audio_queue.get(timeout=1)
                
                # Add to buffer and remove old data if needed
                audio_buffer.append(audio_data)
                if len(audio_buffer) > buffer_max_size:
                    audio_buffer.pop(0)
                
                # Process audio every 0.5 seconds
                if len(audio_buffer) % (buffer_max_size // 4) == 0:
                    # Convert buffer to audio data
                    audio = b''.join(audio_buffer)
                    
                    # Use speech recognition to detect wake word
                    source = sr.AudioData(audio, RATE, 2)
                    try:
                        text = self.recognizer.recognize_google(source).lower()
                        if WAKE_WORD in text:
                            print(f"Wake word detected: '{text}'")
                            self.wake_word_detected = True
                            return True
                    except sr.UnknownValueError:
                        pass  # Speech wasn't understood
                    except sr.RequestError:
                        print("Could not request results from speech recognition service")
            
            except queue.Empty:
                continue
            except Exception as e:
                print(f"Error in wake word detection: {e}")
                
        return False

def record_audio(seconds=5, sample_rate=44100):
    """Record audio from microphone for a specified duration."""
    p = pyaudio.PyAudio()
    
    print(f"Recording for {seconds} seconds...")
    
    stream = p.open(format=FORMAT,
                    channels=CHANNELS,
                    rate=sample_rate,
                    input=True,
                    frames_per_buffer=CHUNK)
    
    frames = []
    for i in range(0, int(sample_rate / CHUNK * seconds)):
        data = stream.read(CHUNK)
        frames.append(data)
    
    print("Recording finished.")
    
    stream.stop_stream()
    stream.close()
    p.terminate()
    
    # Save the audio to a temporary file
    with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as temp_file:
        temp_filename = temp_file.name
    
    wf = wave.open(temp_filename, 'wb')
    wf.setnchannels(CHANNELS)
    wf.setsampwidth(p.get_sample_size(FORMAT))
    wf.setframerate(sample_rate)
    wf.writeframes(b''.join(frames))
    wf.close()
    
    return temp_filename

def run_assistant():
    """Run the voice assistant with wake word detection and speech-to-text."""
    # Get API key from environment variable
    api_key = os.getenv("ELEVENLABS_KEY")
    
    if not api_key:
        print("Error: ELEVENLABS_KEY environment variable not set.")
        print("Please set this variable or create a .env file with this variable.")
        return
    
    try:
        while True:
            # Create a fresh detector for each iteration
            detector = WakeWordDetector()
            detector.start_listening()
            
            try:
                if detector.detect_wake_word():
                    # Record audio for transcription
                    audio_file = record_audio(seconds=5)
                    
                    # Transcribe audio
                    transcript = detector.transcribe_with_elevenlabs(audio_file)
                    
                    if transcript:
                        print("\nTranscript:")
                        print(transcript)
                        # Here you could process the transcript or take actions
                        # based on what was said
                    else:
                        print("\nNo transcript obtained or error occurred.")
                    
                    # Clean up
                    os.remove(audio_file)
                    
                    # IMPORTANT: Properly close the current detector
                    detector.stop_listening()
            
            except Exception as e:
                print(f"Error during processing: {e}")
                
            # Always make sure we clean up the detector before the next iteration
            try:
                detector.stop_listening()
            except:
                pass
                
            time.sleep(1)  # Short delay before restarting
    
    except KeyboardInterrupt:
        print("\nStopping assistant.")
        try:
            detector.stop_listening()
        except:
            pass

def main():
    print("Initializing voice assistant...")
    print("========================")
    print("Say 'Hey Aggie' followed by your request")
    
    run_assistant()

if __name__ == "__main__":
    main()
