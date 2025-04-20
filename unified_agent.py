import os
import time
import queue
import threading
import tempfile
import audioop
import pyaudio
import wave
import speech_recognition as sr
from agent import geminiAgent, handle_chrome_command, handle_general_close_command, handle_type_command, open_app_or_website

# --- Config ---
WAKE_WORD = "steven"
SILENCE_THRESHOLD = int(os.getenv("SOUND_THRESHOLD", 500))
SILENCE_DURATION = 3.0
CHUNK = 1024
FORMAT = pyaudio.paInt16
CHANNELS = 1
RATE = 16000

class UnifiedAgent:
    def __init__(self):
        self.recognizer = sr.Recognizer()
        self.audio_queue = queue.Queue()
        self.recording_frames = []
        self.listening_for_wake_word = False
        self.recording_active = False
        self.exit_requested = False
        self.p = pyaudio.PyAudio()
        self.stream = None
        self.silent_chunks = 0
        self.chunks_per_second = RATE / CHUNK
        self.silent_chunks_threshold = int(SILENCE_DURATION * self.chunks_per_second)
        self.gemini_agent = geminiAgent()

    def start(self):
        print(f"Listening for wake word: '{WAKE_WORD}'...")
        self.listening_for_wake_word = True
        self.recording_active = False
        self.stream = self.p.open(
            format=FORMAT,
            channels=CHANNELS,
            rate=RATE,
            input=True,
            frames_per_buffer=CHUNK,
            stream_callback=self._wake_word_callback
        )
        self.stream.start_stream()
        wake_word_thread = threading.Thread(target=self._detect_wake_word)
        wake_word_thread.daemon = True
        wake_word_thread.start()
        try:
            while not self.exit_requested:
                time.sleep(0.1)
        except KeyboardInterrupt:
            print("\nStopping unified agent.")
        finally:
            self.stop()

    def stop(self):
        self.exit_requested = True
        if self.stream:
            self.stream.stop_stream()
            self.stream.close()
        self.p.terminate()

    def _wake_word_callback(self, in_data, frame_count, time_info, status):
        self.audio_queue.put(in_data)
        return (in_data, pyaudio.paContinue)

    def _detect_wake_word(self):
        audio_buffer = []
        buffer_max_size = int(RATE / CHUNK * 1000)
        while self.listening_for_wake_word and not self.exit_requested:
            try:
                audio_data = self.audio_queue.get(timeout=1)
                audio_buffer.append(audio_data)
                if len(audio_buffer) > buffer_max_size:
                    audio_buffer.pop(0)
                if len(audio_buffer) % (buffer_max_size // 500) == 0:
                    audio = b''.join(audio_buffer)
                    source = sr.AudioData(audio, RATE, 2)
                    try:
                        text = self.recognizer.recognize_google(source).lower()
                        print(f"Heard: '{text}'")
                        if WAKE_WORD in text:
                            print(f"\nWake word detected! Starting to record...")
                            self.stop_wake_word_detection()
                            self.start_recording()
                            return
                    except sr.UnknownValueError:
                        pass
                    except sr.RequestError as e:
                        print(f"Speech recognition error: {e}")
            except queue.Empty:
                continue
            except Exception as e:
                print(f"Error in wake word detection: {e}")

    def stop_wake_word_detection(self):
        self.listening_for_wake_word = False
        if self.stream:
            self.stream.stop_stream()
            self.stream.close()
            self.stream = None

    def start_recording(self):
        self.recording_frames = []
        self.silent_chunks = 0
        self.recording_active = True
        self.stream = self.p.open(
            format=FORMAT,
            channels=CHANNELS,
            rate=RATE,
            input=True,
            frames_per_buffer=CHUNK,
            stream_callback=self._recording_callback
        )
        self.stream.start_stream()
        while self.recording_active and not self.exit_requested:
            time.sleep(0.1)
        if self.recording_frames and not self.exit_requested:
            self._process_recording()

    def _recording_callback(self, in_data, frame_count, time_info, status):
        if self.recording_active:
            self.recording_frames.append(in_data)
            rms = audioop.rms(in_data, 2)
            if rms < SILENCE_THRESHOLD:
                self.silent_chunks += 1
                if self.silent_chunks % int(self.chunks_per_second) == 0:
                    seconds = self.silent_chunks / self.chunks_per_second
                    print(f"Silence detected for {seconds:.1f}s")
                if self.silent_chunks >= self.silent_chunks_threshold:
                    print(f"\nSilence threshold reached ({SILENCE_DURATION}s). Stopping recording.")
                    self.recording_active = False
            else:
                if self.silent_chunks > 0:
                    print("Sound detected, resetting silence counter.")
                self.silent_chunks = 0
        return (in_data, pyaudio.paContinue)

    def _process_recording(self):
        print("Processing recorded audio...")
        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as temp_file:
            temp_filename = temp_file.name
        wf = wave.open(temp_filename, 'wb')
        wf.setnchannels(CHANNELS)
        wf.setsampwidth(self.p.get_sample_size(FORMAT))
        wf.setframerate(RATE)
        wf.writeframes(b''.join(self.recording_frames))
        wf.close()
        recognizer = sr.Recognizer()
        with sr.AudioFile(temp_filename) as source:
            audio = recognizer.record(source)
        try:
            transcript = recognizer.recognize_google(audio)
            print(f"Transcript: {transcript}")
            self.handle_transcript(transcript)
        except Exception as e:
            print(f"Could not transcribe audio: {e}")
        os.remove(temp_filename)
        self.start()

    def handle_transcript(self, transcript):
        # Try all command handlers in order
        if handle_type_command(transcript):
            print(f"[ACTION] Typed: {transcript}")
            return
        if handle_chrome_command(transcript):
            print(f"[ACTION] Chrome command: {transcript}")
            return
        if handle_general_close_command(transcript):
            print(f"[ACTION] General close: {transcript}")
            return
        open_app_or_website(transcript)
        print(f"[ACTION] Open app or website: {transcript}")

if __name__ == "__main__":
    UnifiedAgent().start()
