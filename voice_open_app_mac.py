import speech_recognition as sr
import os
import time
import pyautogui
import platform
import subprocess
import re

IS_MAC = platform.system() == 'Darwin'

if not IS_MAC:
    print("This script is intended for macOS only.")
    exit(1)

CHROME_PATH = "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"

APP_COMMANDS = {
    "chrome": CHROME_PATH,
    "calculator": "open -a Calculator",
    # Add more mappings as needed
}

CHROME_KEYWORDS = [
    (['open a new tab', 'new tab', 'open tab'], lambda: pyautogui.hotkey('command', 't')),
    (['close a tab', 'close tab'], lambda: pyautogui.hotkey('command', 'w')),
    (['close the current window', 'close window', 'exit window', 'close chrome'], lambda: pyautogui.hotkey('command', 'shift', 'w')),
    # Scrolling handled separately for variable amounts
]

SCROLL_SYNONYMS = {
    'down': -1,
    'up': 1
}
SCROLL_INTENSITY = {
    'a lot': 600,
    'a little': 100,
    'little': 100,
    'lot': 600,
    '': 300  # default
}

NUMBER_WORDS = {
    'one': 1, 'two': 2, 'three': 3, 'four': 4, 'five': 5,
    'six': 6, 'seven': 7, 'eight': 8, 'nine': 9, 'ten': 10
}

POPULAR_SITES = {
    'youtube': 'https://www.youtube.com',
    'facebook': 'https://www.facebook.com',
    'twitter': 'https://www.twitter.com',
    'gmail': 'https://mail.google.com',
    'reddit': 'https://www.reddit.com',
    'github': 'https://www.github.com',
    'google': 'https://www.google.com',
    # Add more as needed
}

GENERAL_CLOSE_KEYWORDS = [
    'close window', 'close the window', 'close program', 'close the program', 'exit window', 'exit program', 'exit the window', 'exit the program'
]

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
    try:
        import AppKit
        active_app = AppKit.NSWorkspace.sharedWorkspace().frontmostApplication().localizedName().lower()
        return 'chrome' in active_app
    except Exception:
        return False

def handle_chrome_command(text):
    for keywords, action in CHROME_KEYWORDS:
        for kw in keywords:
            if kw in text:
                if is_chrome_focused():
                    action()
                    return True
    scroll_parsed = parse_scroll_command(text)
    if scroll_parsed and is_chrome_focused():
        scroll_amt, times = scroll_parsed
        for _ in range(times):
            pyautogui.scroll(scroll_amt)
            time.sleep(0.1)
        return True
    return False

def open_chrome_and_url(url):
    if is_chrome_focused():
        pyautogui.hotkey('command', 't')
        time.sleep(0.2)
        pyautogui.typewrite(url)
        pyautogui.press('enter')
    else:
        subprocess.Popen(['open', '-a', 'Google Chrome', url])
    print(f"Opened Chrome to {url}")

def handle_web_command(text):
    text = text.lower()
    for trigger in ['open ', 'go to ']:
        if text.startswith(trigger):
            site = text[len(trigger):].strip()
            for key, url in POPULAR_SITES.items():
                if key in site:
                    open_chrome_and_url(url)
                    return True
    if text.startswith('search for '):
        query = text[len('search for '):].strip()
        if query.endswith('.com') or query.endswith('.org') or query.endswith('.net'):
            url = f'https://{query}' if not query.startswith('http') else query
            open_chrome_and_url(url)
        else:
            url = f'https://www.google.com/search?q={query.replace(' ', '+')}'
            open_chrome_and_url(url)
        return True
    return False

def open_app(app_name):
    command = APP_COMMANDS.get(app_name.lower())
    if command:
        try:
            if app_name.lower() == 'chrome':
                subprocess.Popen(['open', '-a', 'Google Chrome'])
            elif command.startswith('open -a'):
                subprocess.Popen(command.split())
            else:
                subprocess.Popen(['open', '-a', app_name.capitalize()])
            print(f"Opened {app_name}")
        except Exception as e:
            print(f"Failed to open {app_name}: {e}")
    else:
        print(f"App '{app_name}' not recognized in dictionary. Using Spotlight...")
        pyautogui.hotkey('command', 'space')
        time.sleep(0.4)
        pyautogui.typewrite(app_name)
        time.sleep(0.2)
        pyautogui.press('enter')
        print(f"Searched and opened {app_name} via Spotlight.")

def handle_general_close_command(text):
    for kw in GENERAL_CLOSE_KEYWORDS:
        if kw in text:
            pyautogui.hotkey('command', 'shift', 'w')
            return True
    return False

def listen_and_execute():
    recognizer = sr.Recognizer()
    mic = sr.Microphone()
    print("Say a command like 'open chrome', 'open youtube', or 'search for cats'...")
    while True:
        with mic as source:
            recognizer.adjust_for_ambient_noise(source)
            audio = recognizer.listen(source)
        try:
            text = recognizer.recognize_google(audio).lower()
            print(f"You said: {text}")
            if handle_general_close_command(text):
                continue
            if handle_chrome_command(text):
                continue
            if handle_web_command(text):
                continue
            if text.startswith("open "):
                app_name = text[5:].strip()
                open_app(app_name)
            else:
                print("Command not recognized. Please say 'open <app name>'.")
        except Exception as e:
            print(f"Could not understand audio: {e}")

if __name__ == "__main__":
    listen_and_execute()
