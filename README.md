# Steven.ai
Steven.ai is an AI-powered accessibility assistant that enables hands-free computer control for users with limited mobility by combining eye gaze tracking, natural language understanding, and multimodal input. This is a fork of the repository of the project we worked togther.

Role: Machine Learning Developer — Led the design and implementation of ML models for real-time gaze tracking and intent recognition, integrating LLMs and multimodal APIs to enhance accessibility and user independence.
## Installation

### 1. Clone the repository
```bash
git clone https://github.com/MatthewTran22/DAVISHACKS.git
cd DAVISHACKS
```

### 2. Create & activate a virtual environment
**macOS/Linux**
```bash
python3 -m venv .venv
source .venv/bin/activate
```
**Windows (PowerShell)**
```powershell
python -m venv .venv
.\.venv\Scripts\Activate
```

### 3. Install dependencies
```bash
pip install --upgrade pip
pip install -r requirements.txt
```

## Configuration
Steven.ai requires the following environment variables:

- `ELEVENLABS_KEY` – Your ElevenLabs API key for text-to-speech synthesis.
- `SOUND_THRESHOLD` – An integer (e.g., `500`) defining the threshold for audio-based triggers (based on your mic).
- `GEMINI_API_KEY` – Your Google Gemini API key for intent-based command execution.

You can provide these via a `.env` file at the project root or export them in your shell.

### A. `.env` file (recommended)
```dotenv
ELEVENLABS_KEY=your_elevenlabs_api_key_here
SOUND_THRESHOLD=0.5
GEMINI_API_KEY=your_gemini_api_key_here
```

### B. Shell export (alternative)
**macOS/Linux**
```bash
export ELEVENLABS_KEY="your_elevenlabs_api_key_here"
export SOUND_THRESHOLD="0.5"
export GEMINI_API_KEY="your_gemini_api_key_here"
```
**Windows (PowerShell)**
```powershell
$env:ELEVENLABS_KEY = "your_elevenlabs_api_key_here"
$env:SOUND_THRESHOLD = "0.5"
$env:GEMINI_API_KEY = "your_gemini_api_key_here"
```

## Usage

Run the prototype:
```bash
python main_qt.py
```

This will launch the GUI and load your configuration. Make sure your virtual environment is active so the environment variables are accessible.

## Troubleshooting

- **.env not loading:** Ensure `python-dotenv` is installed and your file is named `.env` in the project root.
- **Env vars missing:** Verify variable names and that you’re in the activated virtual environment.
- **Dependency errors:** Re-run `pip install -r requirements.txt` or update pip.

---

Ready to explore hands-free computing? Enjoy Steven.ai!
