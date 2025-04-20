import time
import os
import numpy as np
import audioop
import tempfile
from pydub import AudioSegment
from pydub.silence import split_on_silence
from dotenv import load_dotenv
import speech_recognition as sr
import threading
import queue
import pyaudio
import wave
from elevenlabs import ElevenLabs
import agent 

# Load environment variables from .env file
load_dotenv()

# Audio recording parameters
CHUNK = 1024
FORMAT = pyaudio.paInt16
CHANNELS = 1
RATE = 16000
WAKE_WORD = "steven"
SILENCE_THRESHOLD = int(os.getenv("SOUND_THRESHOLD"))  # Adjust based on your microphone and environment
SILENCE_DURATION = 3.0   # Seconds of silence to end recording

# Initialize ElevenLabs client
client = ElevenLabs(
    api_key=os.getenv("ELEVENLABS_KEY")
)

class VoiceAssistant:
    def __init__(self):
        # Initialize recognizer for wake word detection
        self.recognizer = sr.Recognizer()
        self.recognizer.energy_threshold = 1000  # Adjust based on your environment
        self.recognizer.dynamic_energy_threshold = True
        
        # Audio processing queues
        self.audio_queue = queue.Queue()
        self.recording_frames = []
        
        # State flags
        self.listening_for_wake_word = False
        self.recording_active = False
        self.exit_requested = False
        
        # PyAudio setup
        self.p = pyaudio.PyAudio()
        self.stream = None
        
        # Silence detection variables
        self.silent_chunks = 0
        self.chunks_per_second = RATE / CHUNK
        self.silent_chunks_threshold = int(SILENCE_DURATION * self.chunks_per_second)
        self.gemini_agent = agent.geminiAgent()
        
    def transcribe_with_elevenlabs(self, audio_file):
        """Transcribe audio file using ElevenLabs API."""
        
        audio_data = open(audio_file, 'rb').read()
        
        transcription = client.speech_to_text.convert(
            file=audio_data,
            model_id="scribe_v1",  # Model to use, for now only "scribe_v1" is supported
            tag_audio_events=True,  # Tag audio events like laughter, applause, etc.
            language_code="eng",    # Language of the audio file
            diarize=True,           # Whether to annotate who is speaking
        )
        print(transcription.text)
        with open("transcription.txt", "w") as file:
            file.write(transcription.text)
            
        return transcription.text
            
    def start(self):
        """Start the voice assistant"""
        self.exit_requested = False
        self.cycle_count = 0
        
        # Start listening for wake word
        self.start_listening_for_wake_word()
        
        # Main processing loop
        try:
            while not self.exit_requested:
                time.sleep(0.1)  # Sleep to prevent CPU hogging
                
                # Periodically recycle resources to prevent memory leaks
                self.cycle_count += 1
                if self.cycle_count > 1000:  # Every ~100 seconds
                    self.recycle_resources()
                    self.cycle_count = 0
                    
        except KeyboardInterrupt:
            print("\nStopping voice assistant.")
        finally:
            self.stop()
            
    def recycle_resources(self):
        """Periodically clean up and reset resources to prevent memory buildup"""
        if not self.recording_active:  # Only recycle when not actively recording
            print("Performing resource cleanup...")
            self.stop_wake_word_detection()
            # Small delay to ensure proper cleanup
            time.sleep(0.5)
            self.start_listening_for_wake_word()
            
    def stop(self):
        """Stop the voice assistant and clean up resources"""
        self.exit_requested = True
        if self.stream:
            self.stream.stop_stream()
            self.stream.close()
            self.stream = None  # Add this line
        self.p.terminate()
        
        # Clear queues and buffers
        while not self.audio_queue.empty():
            try:
                self.audio_queue.get_nowait()
            except queue.Empty:
                break
        self.recording_frames = []
            
    def start_listening_for_wake_word(self):
        """Start listening for the wake word"""
        # Clean up previous threads if they exist
        if hasattr(self, 'wake_word_thread') and self.wake_word_thread.is_alive():
            # Give the thread time to terminate
            self.listening_for_wake_word = False
            time.sleep(0.5)
        
        print(f"Listening for wake word: '{WAKE_WORD}'...")
        self.listening_for_wake_word = True
        self.recording_active = False
        
        # Start the audio stream with callback
        self.stream = self.p.open(
            format=FORMAT,
            channels=CHANNELS,
            rate=RATE,
            input=True,
            frames_per_buffer=CHUNK,
            stream_callback=self._wake_word_callback
        )
        self.stream.start_stream()
        
        # Start wake word detection thread
        self.wake_word_thread = threading.Thread(target=self._detect_wake_word)
        self.wake_word_thread.daemon = True
        self.wake_word_thread.start()
    
    def _wake_word_callback(self, in_data, frame_count, time_info, status):
        """Audio callback for wake word detection mode"""
        self.audio_queue.put(in_data)
        return (in_data, pyaudio.paContinue)
    
    def _detect_wake_word(self):
        """Process audio queue to detect wake word"""
        # Buffer to accumulate audio data
        audio_buffer = []
        buffer_max_size = int(RATE / CHUNK * 5)  # Reduced from 1000 to 5 seconds
        
        while self.listening_for_wake_word and not self.exit_requested:
            try:
                # Get audio data from queue
                audio_data = self.audio_queue.get(timeout=1)
                
                # Add to buffer and remove old data if needed
                audio_buffer.append(audio_data)
                if len(audio_buffer) > buffer_max_size:
                    audio_buffer.pop(0)
                
                # Process audio every 0.5 seconds
                if len(audio_buffer) % (buffer_max_size // 10) == 0:
                    # Convert buffer to audio data
                    audio = b''.join(audio_buffer)
                    
                    # Use speech recognition to detect wake word
                    source = sr.AudioData(audio, RATE, 2)
                    try:
                        text = self.recognizer.recognize_google(source).lower()
                        print(f"Heard: '{text}'")
                        
                        if WAKE_WORD in text:
                            print(f"\nWake word detected! Starting to record...")
                            # Switch to recording mode
                            self.stop_wake_word_detection()
                            self.start_recording()
                            return
                    except sr.UnknownValueError:
                        pass  # Speech wasn't understood
                    except sr.RequestError:
                        print("Could not request results from speech recognition service")
            
            except queue.Empty:
                continue
            except Exception as e:
                print(f"Error in wake word detection: {e}")
    
    def stop_wake_word_detection(self):
        """Stop listening for wake word"""
        self.listening_for_wake_word = False
        if self.stream:
            self.stream.stop_stream()
            self.stream.close()
            self.stream = None
    
    def start_recording(self):
        """Start recording audio with silence detection"""
        # Clear previous recording frames
        self.recording_frames = []
        self.silent_chunks = 0
        self.silence_start_time = None  # Track when silence begins
        self.recording_active = True
        
        # Start new audio stream for recording
        self.stream = self.p.open(
            format=FORMAT,
            channels=CHANNELS,
            rate=RATE,
            input=True,
            frames_per_buffer=CHUNK,
            stream_callback=self._recording_callback
        )
        self.stream.start_stream()
        
        # Wait for recording to complete (will be stopped by silence detection)
        while self.recording_active and not self.exit_requested:
            time.sleep(0.1)
        
        # Process the recorded audio
        if self.recording_frames and not self.exit_requested:
            self._process_recording()
    
    def _recording_callback(self, in_data, frame_count, time_info, status):
        """Audio callback for recording mode with silence detection"""
        if self.recording_active:
            # Store audio frame
            self.recording_frames.append(in_data)
            
            # Check for silence using RMS value
            rms = audioop.rms(in_data, 2)  # 2 bytes per sample for paInt16
            
            # Current time for absolute timing
            current_time = time.time()
            
            if rms < SILENCE_THRESHOLD:
                # If this is the start of silence, record the timestamp
                if self.silence_start_time is None:
                    self.silence_start_time = current_time
                    self.silent_chunks = 1  # Keep this for backward compatibility
                    print("Silence detected, starting timer...")
                else:
                    # Calculate silence duration from absolute timestamps
                    silence_duration = current_time - self.silence_start_time
                    self.silent_chunks += 1  # Keep updating for backward compatibility
                    
                    # Print silence progress every second (approximately)
                    if self.silent_chunks % int(self.chunks_per_second) == 0:
                        print(f"Silence detected for {silence_duration:.1f}s")
                    
                    # Check if silence duration threshold reached using absolute time
                    if silence_duration >= SILENCE_DURATION:
                        print(f"\nSilence threshold reached ({silence_duration:.1f}s). Stopping recording.")
                        self.recording_active = False
            else:
                # Reset timer if sound detected
                if self.silence_start_time is not None:
                    print("Sound detected, resetting silence timer.")
                    self.silence_start_time = None
                    self.silent_chunks = 0
        
        return (in_data, pyaudio.paContinue)
    
    def _process_recording(self):
        """Process the recorded audio and send for transcription"""
        print("Processing recorded audio...")
        
        # Save the audio to a temporary file
        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as temp_file:
            temp_filename = temp_file.name
        
        wf = wave.open(temp_filename, 'wb')
        wf.setnchannels(CHANNELS)
        wf.setsampwidth(self.p.get_sample_size(FORMAT))
        wf.setframerate(RATE)
        wf.writeframes(b''.join(self.recording_frames))
        wf.close()
        
        # Get recording duration
        frames_count = len(self.recording_frames)
        duration = frames_count * CHUNK / RATE
        print(f"Recording saved: {duration:.2f} seconds")
        
        # Transcribe audio using ElevenLabs client
        transcript = self.transcribe_with_elevenlabs(temp_filename)
        
        if transcript:
            print("\nTranscript:")
            print(transcript)
            # Here you could process the transcript or take actions
        else:
            print("\nNo transcript obtained or error occurred.")
        
        # Clean up
        os.remove(temp_filename)
        self.gemini_agent.run()
        # Return to listening for wake word
        self.start_listening_for_wake_word()

def run_assistant():
    """Run the voice assistant with wake word detection and silence detection."""
    # Get API key from environment variable
    api_key = os.getenv("ELEVENLABS_KEY")
    
    if not api_key:
        print("Error: ELEVENLABS_KEY environment variable not set.")
        print("Please set this variable or create a .env file with this variable.")
        return
    
    assistant = VoiceAssistant()
    assistant.start()
      
def main():
    print("Voice Assistant with Wake Word and Silence Detection")
    print("==================================================")
    print(f"Say '{WAKE_WORD}' to activate, then speak your request.")
    print(f"Recording will stop after {SILENCE_DURATION} seconds of silence.")
    print("Press Ctrl+C to exit.")
    print()
    
    run_assistant()

if __name__ == "__main__":
    main()