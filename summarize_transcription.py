import os
from google import genai

def summarize_transcription(transcription_path):
    with open(transcription_path, 'r', encoding='utf-8') as f:
        text = f.read()
    client = genai.Client(api_key="AIzaSyB35N83uAdd5cjwfXqkLH9T9_PhWHTMSb8")
    prompt = f"Summarize the following conversation in simple, accessible language for someone who may have difficulty reading long text.\n\nConversation:\n{text}"
    response = client.models.generate_content(
        model='gemini-2.0-flash',
        contents=prompt
    )
    return response.text

if __name__ == "__main__":
    summary = summarize_transcription('transcription.txt')
    print("Summary:")
    print(summary)
