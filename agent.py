# parse_intents.py
import os
import re
import json
import platform
import subprocess
from google import genai

class geminiAgent():
    def __init__(self):
        self.client = genai.Client(api_key=os.getenv('GEMINI_API_KEY'))

    def extract_open_intents(self, transcript_path: str):
        with open(transcript_path, 'r') as f:
            transcript = f.read().strip()
        
        system = (
            "You are an accessibility assistant.  Parse the user's transcript "
            "and extract every command to open an application. Correct spelling if necessary. "
            "Return only a JSON object with two arrays: "
            "\"actions\": [...], \"apps\": [...]."
        )
        user = f"Transcript:\n{transcript}\n\nReply **only** with that JSON."

        resp = self.client.models.generate_content(
            model='gemini-2.0-flash',
            contents=[system, user],
        )
        raw = resp.text.strip()
        print("=== raw response ===\n", raw, "\n====================")

        m = re.search(r'\{.*\}', raw, re.DOTALL)
        if not m:
            return [], []
        data = json.loads(m.group(0))
        return data.get('actions', []), data.get('apps', [])

    def open_app(self, app_name: str):
        """
        Cross‑platform app/URL opener.
        If on macOS, uses `open -a`.
        If on Windows, uses `start`.
        Otherwise tries `xdg-open` (Linux).
        Falls back to webbrowser for known web apps.
        """
        system = platform.system()
        
        # If it's a well‑known web app, open in browser:
        web_apps = {'facebook', 'youtube', 'twitter'}
        if app_name.lower() in web_apps:
            import webbrowser
            webbrowser.open(f'https://www.{app_name.lower()}.com')
            return
        
        try:
            if system == 'Darwin':  # macOS
                subprocess.Popen(['open', '-a', app_name])
            elif system == 'Windows':
                # Note: 'start' is a shell builtin; we need shell=True
                subprocess.Popen(f'start "" "{app_name}"', shell=True)
            else:
                # Linux fallback
                subprocess.Popen(['xdg-open', app_name])
        except Exception as e:
            print(f"❌ Failed to open {app_name} on {system}: {e}")

    def run(self):
        os.environ.setdefault("GEMINI_API_KEY", "<YOUR_KEY_HERE>")
        actions, apps = self.extract_open_intents("transcription.txt")
        print("Actions:", actions)
        print("  Apps: ", apps)

        for act, app in zip(actions, apps):
            if act.lower() == 'open':
                self.open_app(app)