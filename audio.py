
import pyaudio
import wave
import requests
import json
import tempfile
import time
import os
from pydub import AudioSegment
from pydub.silence import split_on_silence
from elevenlabs import ElevenLabs
from dotenv import load_dotenv

load_dotenv()

client = ElevenLabs(
  api_key=os.getenv("ELEVENLABS_KEY")
)

def record_audio(seconds=5, sample_rate=44100):
    """Record audio from microphone for a specified duration."""
    CHUNK = 1024
    FORMAT = pyaudio.paInt16
    CHANNELS = 1
    
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

def transcribe_with_elevenlabs(audio_file, api_key):
    """Transcribe audio file using ElevenLabs API."""
    url = "https://api.elevenlabs.io/v1/speech-to-text"
    
    audio_data = open(audio_file, 'rb').read()
    
    transcription = client.speech_to_text.convert(
      file=audio_data,
      model_id="scribe_v1", # Model to use, for now only "scribe_v1" is supported
      tag_audio_events=True, # Tag audio events like laughter, applause, etc.
      language_code="eng", # Language of the audio file. If set to None, the model will detect the language automatically.
      diarize=True, # Whether to annotate who is speaking
    )
    print(transcription.text)

def segment_audio(audio_file):
    """Split audio file into segments based on silence."""
    sound = AudioSegment.from_wav(audio_file)
    
    # Split audio into chunks based on silence
    chunks = split_on_silence(
        sound,
        min_silence_len=500,  # minimum silence length in ms
        silence_thresh=-40,   # silence threshold in dB
        keep_silence=300      # keep 300ms of silence at the beginning and end
    )
    
    # Create temporary files for each chunk
    chunk_files = []
    for i, chunk in enumerate(chunks):
        chunk_file = f"temp_chunk_{i}.wav"
        chunk.export(chunk_file, format="wav")
        chunk_files.append(chunk_file)
    
    return chunk_files

def live_speech_to_text(api_key, duration=5, continuous=False):
    """Perform live speech-to-text conversion."""
    
    try:
        while True:
            # Record audio
            audio_file = record_audio(seconds=duration)
            
            # Transcribe audio
            transcript = transcribe_with_elevenlabs(audio_file, api_key)
            
            if transcript:
                print("\nTranscript:")
                print(transcript)
            else:
                print("\nNo transcript obtained or error occurred.")
            
            # Clean up
            os.remove(audio_file)
            
            if not continuous:
                break
            
            print("\nReady for next recording. Press Ctrl+C to stop.")
            time.sleep(1)
            
    except KeyboardInterrupt:
        print("\nStopping live transcription.")

def main():
    # Replace with your actual ElevenLabs API key
    api_key = "YOUR_ELEVENLABS_API_KEY"
    
    print("ElevenLabs Live Speech-to-Text")
    print("==============================")
    
    # Choose mode
    print("1. Single recording mode")
    print("2. Continuous recording mode")
    choice = input("Choose mode (1/2): ")
    
    duration = int(input("Recording duration per segment (seconds): "))
    
    if choice == "1":
        live_speech_to_text(api_key, duration=duration, continuous=False)
    elif choice == "2":
        live_speech_to_text(api_key, duration=duration, continuous=True)
    else:
        print("Invalid choice")
        
if __name__ == "__main__":
    main()