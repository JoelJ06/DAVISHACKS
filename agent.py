# parse_intents.py
import os
import re
import json
import platform
import subprocess
from google import genai
# Load environment variables from .env file
from dotenv import load_dotenv
load_dotenv()
key = os.getenv('GEMINI_API_KEY')

import pyautogui
import time

# Platform checks
IS_WINDOWS = platform.system() == 'Windows'
IS_MAC = platform.system() == 'Darwin'

# Chrome paths
CHROME_PATH = None
if IS_WINDOWS:
    CHROME_PATH = r"C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe"
elif IS_MAC:
    CHROME_PATH = "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"

# App command dictionary (expand as needed)
APP_COMMANDS = {
    "chrome": CHROME_PATH,
    "notepad": "notepad.exe" if IS_WINDOWS else None,
    "calculator": "calc.exe" if IS_WINDOWS else "open -a Calculator" if IS_MAC else None,
}

# Popular sites
POPULAR_SITES = {
    'youtube': 'https://www.youtube.com',
    'facebook': 'https://www.facebook.com',
    'twitter': 'https://www.twitter.com',
    'gmail': 'https://mail.google.com',
    'reddit': 'https://www.reddit.com',
    'github': 'https://www.github.com',
    'google': 'https://www.google.com',
}


# Scroll helpers
SCROLL_SYNONYMS = {'down': -1, 'up': 1}
SCROLL_INTENSITY = {'a lot': 600, 'a little': 100, 'little': 100, 'lot': 600, '': 300}
NUMBER_WORDS = {
    'one': 1, 'two': 2, 'three': 3, 'four': 4, 'five': 5,
    'six': 6, 'seven': 7, 'eight': 8, 'nine': 9, 'ten': 10
}

def parse_scroll_command(text):
    text = text.lower()
    match = re.search(r'scroll (up|down)(?: (a lot|a little|lot|little|\d+|one|two|three|four|five|six|seven|eight|nine|ten)?(?: times?)?)?', text)
    if not match:
        return None
    direction = match.group(1)
    amount_word = match.group(2) or ''
    if amount_word in SCROLL_INTENSITY:
        scroll_amt = SCROLL_INTENSITY[amount_word]
        times = 1
    elif amount_word.isdigit():
        scroll_amt = SCROLL_INTENSITY['']
        times = int(amount_word)
    elif amount_word in NUMBER_WORDS:
        scroll_amt = SCROLL_INTENSITY['']
        times = NUMBER_WORDS[amount_word]
    else:
        scroll_amt = SCROLL_INTENSITY['']
        times = 1
    scroll_amt = scroll_amt * SCROLL_SYNONYMS[direction]
    return scroll_amt, times

def is_chrome_focused():
    if IS_WINDOWS:
        try:
            import win32gui
            hwnd = win32gui.GetForegroundWindow()
            window_title = win32gui.GetWindowText(hwnd).lower()
            return 'chrome' in window_title
        except Exception:
            return False
    elif IS_MAC:
        try:
            import AppKit
            active_app = AppKit.NSWorkspace.sharedWorkspace().frontmostApplication().localizedName().lower()
            return 'chrome' in active_app
        except Exception:
            return False
    return False

def handle_chrome_command(text):
    text = text.lower()
    # Tab/window commands
    if 'tab' in text or 'window' in text or 'chrome' in text:
        if 'new tab' in text or 'open tab' in text:
            if is_chrome_focused():
                if IS_WINDOWS:
                    pyautogui.hotkey('ctrl', 't')
                elif IS_MAC:
                    pyautogui.hotkey('command', 't')
                return True
        elif 'close tab' in text:
            if is_chrome_focused():
                if IS_WINDOWS:
                    pyautogui.hotkey('ctrl', 'w')
                elif IS_MAC:
                    pyautogui.hotkey('command', 'w')
                return True
        elif 'close window' in text or 'exit window' in text or 'close chrome' in text:
            if is_chrome_focused():
                if IS_WINDOWS:
                    pyautogui.hotkey('alt', 'f4')
                elif IS_MAC:
                    pyautogui.hotkey('command', 'shift', 'w')
                return True
    # Scroll
    scroll_parsed = parse_scroll_command(text)
    if scroll_parsed:
        scroll_amt, times = scroll_parsed
        for _ in range(times):
            pyautogui.scroll(scroll_amt)
            time.sleep(0.1)
        return True
    return False

class geminiAgent():
    def __init__(self):
        self.client = genai.Client(api_key=os.getenv('GEMINI_API_KEY'))

    def cleanup(self):
        """Release resources used by the agent"""
        # Close any open client sessions
        if hasattr(self, 'client') and self.client is not None:
            # Most API clients have a close() method
            if hasattr(self.client, 'close') and callable(self.client.close):
                self.client.close()
            # Set to None to help garbage collection
            self.client = None
        print("Agent resources cleaned up")

    def extract_open_intents(self, transcript_path: str):
        with open(transcript_path, 'r') as f:
            transcript = f.read().strip()
        
        system = (
            "You are an accessibility assistant.  Parse the user's transcript "
            "and extract every command to open an application. Correct spelling if necessary, to the appropriate full application name."
            "As an example, chrome should autocorrect to Google Chrome."
            "The commands are open, scroll, type, close."
            "Synonyms of commands should also be corrected to the command itself."
            "Prune unnecessary words from the command, such as 'open the app' to 'open app'."
            "When the command is 'close', automatically convert websites to 'tab' and browser names to 'window'."
            "Make sure everything is lowercase"
            "Return only a JSON object with two arrays: "
            "The actions array should contain the commands, and the arguments array should contain the arguments."
            "\"actions\": [...], \"arguments\": [...]."
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
        return data.get('actions', []), data.get('arguments', [])
    
    def type_command(self, args):
        pyautogui.write(args)
        pyautogui.press('enter')
    
    def is_chrome_focused():
        if IS_WINDOWS:
            try:
                import win32gui
                hwnd = win32gui.GetForegroundWindow()
                window_title = win32gui.GetWindowText(hwnd).lower()
                return 'chrome' in window_title
            except Exception:
                return False
        elif IS_MAC:
            try:
                import AppKit
                active_app = AppKit.NSWorkspace.sharedWorkspace().frontmostApplication().localizedName().lower()
                return 'chrome' in active_app
            except Exception:
                return False
        return False

    def scroll_command(self, args):
        match = re.search(r'scroll (up|down)(?: (a lot|a little|lot|little|\d+|one|two|three|four|five|six|seven|eight|nine|ten)?(?: times?)?)?', args)
        if not match:
            return None
        direction = match.group(1)
        amount_word = match.group(2) or ''
        if amount_word in SCROLL_INTENSITY:
            scroll_amt = SCROLL_INTENSITY[amount_word]
            times = 1
        elif amount_word.isdigit():
            scroll_amt = SCROLL_INTENSITY['']
            times = int(amount_word)
        elif amount_word in NUMBER_WORDS:
            scroll_amt = SCROLL_INTENSITY['']
            times = NUMBER_WORDS[amount_word]
        else:
            scroll_amt = SCROLL_INTENSITY['']
            times = 1
        scroll_amt = scroll_amt * SCROLL_SYNONYMS[direction]
        for _ in range(times):
            pyautogui.scroll(scroll_amt)
            time.sleep(0.1)
    
    def close_app(self, app_name: str):
        system = platform.system()
        
        if app_name == 'window' and system == 'Windows':
            pyautogui.hotkey('alt', 'f4')
        elif app_name == 'window' and system == 'Darwin':
            pyautogui.hotkey('command', 'shift', 'w')
        elif app_name == 'tab' and system == 'Windows': 
            pyautogui.hotkey('ctrl', 'w')
        elif app_name == 'tab' and system == 'Darwin':
            pyautogui.hotkey('command', 'w')
        
        
        
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
        if app_name in web_apps:
            import webbrowser
            webbrowser.open(f'https://www.{app_name.lower()}.com')
            return
        chrome = is_chrome_focused()
        if app_name == 'tab' and system == 'Windows':
            pyautogui.hotkey('ctrl', 't')
            return
        elif app_name == 'tab' and system == 'Darwin':
            pyautogui.hotkey('command', 't')
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
            
    
    def handle_transcript(self, actions, apps):
      # Try all command handlers in order
      if actions.lower() == 'type':
          self.type_command(apps.lower())
          return
      if actions.lower() == 'scroll':
          self.scroll_command(apps.lower())
          return
      if actions.lower() == 'open':
        self.open_app(apps.lower())
        return
      if actions.lower() == 'close':
        self.close_app(apps.lower())
        return
    
      
    def run(self):
        # os.environ.setdefault("GEMINI_API_KEY", "<YOUR_KEY_HERE>")
        actions, args = self.extract_open_intents("transcription.txt")
        print("Actions:", actions)
        print("  Args: ", args)
    
        for act, args in zip(actions, args):
            self.handle_transcript(act, args)
        
        return actions, args  # Return the results for potential further processing
