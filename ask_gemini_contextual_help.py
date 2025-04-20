import os
from google import genai

def ask_gemini_contextual_help(context_description):
    client = genai.Client(api_key="AIzaSyB35N83uAdd5cjwfXqkLH9T9_PhWHTMSb8")
    prompt = f"A user with accessibility needs is currently using the following app or screen: {context_description}. Please provide a simple, step-by-step explanation of what they can do on this screen, and how to use it effectively. Focus on accessibility tips and easy-to-understand instructions."
    response = client.models.generate_content(
        model='gemini-2.0-flash',
        contents=prompt
    )
    return response.text

if __name__ == "__main__":
    context = input("Describe the current app or screen (e.g., 'Gmail inbox', 'YouTube video page', 'Windows desktop'): ")
    answer = ask_gemini_contextual_help(context)
    print("\nGemini Accessibility Help:\n")
    print(answer)
