import os
from google import genai

client = genai.Client(api_key="AIzaSyB35N83uAdd5cjwfXqkLH9T9_PhWHTMSb8")
response = client.models.generate_content(
    model='gemini-2.0-flash',
    contents='Explain the benefits of using environment variables.'
)
print(response.text)