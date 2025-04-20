import speech_recognition as sr
import os
import time
import pyautogui
import platform
import subprocess
import re

IS_WINDOWS = platform.system() == 'Windows'

if not IS_WINDOWS:
    print("This script is intended for Windows only.")
    exit(1)

CHROME_PATH = r"C:\Program Files\Google\Chrome\Application\chrome.exe"

APP_COMMANDS = {
    "chrome": CHROME_PATH,
    "calculator": "calc.exe",
    # Add more mappings as needed
}

CHROME_KEYWORDS = [
    (['open a new tab', 'new tab', 'open tab'], lambda: pyautogui.hotkey('ctrl', 't')),
    (['close a tab', 'close tab'], lambda: pyautogui.hotkey('ctrl', 'w')),
    (['close the current window', 'close window', 'exit window', 'close chrome'], lambda: pyautogui.hotkey('alt', 'f4')),
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
    match = re.search(r'scroll (up|down)(?: (a lot|a little|lot|little|\\d+|one|two|three|four|five|six|seven|eight|nine|ten)?(?: times?)?)?', text)
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
    # On Windows, check for Chrome in the active window title
    try:
        import win32gui
        window = win32gui.GetForegroundWindow()
        title = win32gui.GetWindowText(window).lower()
        return 'chrome' in title
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

def open_app_or_website(text):
    text = text.lower()
    for site, url in POPULAR_SITES.items():
        if site in text:
            subprocess.Popen([CHROME_PATH, url])
            return
    for app, cmd in APP_COMMANDS.items():
        if app in text:
            subprocess.Popen(cmd if isinstance(cmd, list) else [cmd])
            return
    if any(ext in text for ext in ['.com', '.org', '.net']):
        url = text if text.startswith('http') else 'https://' + text.replace(' ', '')
        subprocess.Popen([CHROME_PATH, url])
        return
    # Try to open as a Windows app
    try:
        os.startfile(text)
    except Exception as e:
        print(f"Could not open application or website '{text}': {e}")

def main():
    recognizer = sr.Recognizer()
    mic = sr.Microphone()
    print("Say the name of the app, website, or Chrome command...")
    while True:
        with mic as source:
            recognizer.adjust_for_ambient_noise(source)
            audio = recognizer.listen(source)
        try:
            text = recognizer.recognize_google(audio)
            print(f"You said: {text}")
            if handle_chrome_command(text):
                return
            open_app_or_website(text)
        except Exception as e:
            print(f"Could not understand audio: {e}")

if __name__ == "__main__":
    main()
