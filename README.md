# STT Service

A clean, production-ready Speech-to-Text microservice built with **FastAPI**, **faster-whisper**, and local **Hugging Face Whisper** support.

It accepts audio files or plain text and returns a **unified structured response** that can be directly consumed by an LLM orchestration layer.

---

## Features

- **`POST /stt/transcribe`** — Upload audio (WAV/MP3), get structured transcription with word-level timestamps
- **`POST /stt/text`** — Submit plain text, get the same structured format (language auto-detected)
- Singleton Whisper model (loaded once, reused across requests)
- Supports built-in faster-whisper models, local CTranslate2/faster-whisper folders, or local Hugging Face Whisper fine-tunes
- Automatic audio normalisation to 16 kHz mono via ffmpeg/pydub
- GPU acceleration when available (CUDA), CPU fallback with int8 quantisation
- Clean error handling and input validation

---

## Project Structure

```
backend/
├── main.py                    # FastAPI app with endpoints
├── stt_service.py             # Whisper transcription logic
├── text_service.py            # Text processing + language detection
├── utils.py                   # Shared response models and audio helpers
frontend/
├── index.html                 # Browser mic evaluation UI
├── script.js                  # Two-model comparison workflow
requirements.txt
README.md
```

---

## Setup

### Prerequisites

- Python 3.10+
- **ffmpeg** installed and on your PATH (required by pydub for audio conversion)

```bash
# macOS
brew install ffmpeg

# Ubuntu / Debian
sudo apt install ffmpeg
```

### Install Dependencies

```bash
# Create and activate virtual environment
python -m venv venv
source venv/bin/activate        # Linux/macOS
# venv\Scripts\activate         # Windows

# Install dependencies
pip install -r requirements.txt

# For GPU support (optional — NVIDIA GPU with CUDA required):
pip install torch --index-url https://download.pytorch.org/whl/cu121
```

> **Note:** On first run, a built-in `faster-whisper` model will be downloaded automatically. If you use a local fine-tuned model, the backend loads it directly from disk instead.

---

## Run Locally

```bash
uvicorn backend.main:app --host 0.0.0.0 --port 8000 --reload
```

The API docs are available at: **http://localhost:8000/docs**

To start with a larger default model:

```bash
WHISPER_MODEL=large-v3 uvicorn backend.main:app --host 0.0.0.0 --port 8000 --reload
```

To start with your own fine-tuned model stored on Drive:

```bash
WHISPER_MODEL=custom \
WHISPER_MODEL_PATH="/absolute/path/to/your/model-folder" \
uvicorn backend.main:app --host 0.0.0.0 --port 8000 --reload
```

Example for a locally synced Google Drive folder on macOS:

```bash
WHISPER_MODEL=custom \
WHISPER_MODEL_PATH="$HOME/Library/CloudStorage/GoogleDrive-your-account/My Drive/models/my-whisper-ft" \
uvicorn backend.main:app --host 0.0.0.0 --port 8000 --reload
```

Important:

- `WHISPER_MODEL_PATH` must point to a local directory on your machine, not the Colab path.
- This backend now supports both of these local folder formats:
- a `faster-whisper` / CTranslate2 export with files such as `model.bin`
- a Hugging Face Whisper folder saved with `save_pretrained()`, usually containing `config.json`, tokenizer files, and model weights
- Your screenshot suggests your `telugu-whisper` folder is the second type, so you do not need to convert it first.
- You can also pass a local directory path directly in the `model_name` form field per request.

If your model was only saved inside Colab at:

```bash
/content/drive/MyDrive/telugu-whisper
```

you need to download or sync that folder to your computer first, then point `WHISPER_MODEL_PATH` to the local copy.

---

## Browser Evaluation Flow

1. Start the backend:

```bash
source venv/bin/activate
uvicorn backend.main:app --host 0.0.0.0 --port 8000 --reload
```

2. Open `frontend/index.html` in your browser.
3. Pick a baseline model and a candidate model.
4. Read the shown phrase aloud and record once.
5. Review the side-by-side JSON output and save your judgement.
6. Export the saved evaluations as JSON when you want to compare runs.

---

## Example Requests

### 1. Transcribe Audio

```bash
curl -X POST http://localhost:8000/stt/transcribe \
  -F "file=@sample.wav"
```

With a language hint:

```bash
curl -X POST http://localhost:8000/stt/transcribe \
  -F "file=@sample.mp3" \
  -F "language=hi"
```

Using your configured custom model:

```bash
curl -X POST http://localhost:8000/stt/transcribe \
  -F "file=@sample.wav" \
  -F "model_name=custom"
```

Using a specific local model directory directly:

```bash
curl -X POST http://localhost:8000/stt/transcribe \
  -F "file=@sample.wav" \
  -F "model_name=/absolute/path/to/your/model-folder"
```

Example for your Telugu fine-tune after downloading it locally:

```bash
curl -X POST http://localhost:8000/stt/transcribe \
  -F "file=@sample.wav" \
  -F "model_name=/absolute/path/to/telugu-whisper"
```

### 2. Process Text

```bash
curl -X POST http://localhost:8000/stt/text \
  -H "Content-Type: application/json" \
  -d '{"text": "Hello, how are you doing today?"}'
```

Telugu text example:

```bash
curl -X POST http://localhost:8000/stt/text \
  -H "Content-Type: application/json" \
  -d '{"text": "నమస్కారం, మీరు ఎలా ఉన్నారు?"}'
```

### 3. Health Check

```bash
curl http://localhost:8000/health
```

---

## Response Format

Both endpoints return the **exact same schema**:

```json
{
  "type": "speech",
  "text": "Hello, how are you?",
  "language": "en",
  "segments": [
    {
      "start": 0.0,
      "end": 2.34,
      "text": "Hello, how are you?"
    }
  ],
  "words": [
    { "word": "Hello,", "start": 0.0, "end": 0.42 },
    { "word": "how",    "start": 0.42, "end": 0.78 },
    { "word": "are",    "start": 0.78, "end": 1.02 },
    { "word": "you?",   "start": 1.02, "end": 2.34 }
  ],
  "metadata": {
    "processing_time": 1.2345,
    "input_length": 5.67
  }
}
```

| Field        | Description                                                    |
|--------------|----------------------------------------------------------------|
| `type`       | `"speech"` for audio input, `"text"` for text input            |
| `text`       | The full processed text                                        |
| `language`   | Detected language code (`en`, `hi`, `te`, etc.)                |
| `segments`   | Timed segments (start/end in seconds, zeroed for text)         |
| `words`      | Word-level timing (zeroed for text input)                      |
| `metadata`   | Processing time (seconds) and input length (seconds or chars)  |

---

## Configuration

| Environment Variable | Default | Description |
|---|---|---|
| `WHISPER_MODEL` | `large-v3-turbo` | Default startup model. Supported values: `tiny`, `base`, `small`, `medium`, `large-v3`, `large-v3-turbo`, or `custom` |
| `WHISPER_MODEL_PATH` | unset | Absolute or resolvable local path to your fine-tuned model directory. Can be either a `faster-whisper` export or a Hugging Face Whisper folder. Used when `WHISPER_MODEL=custom` or when `model_name=custom` is sent to the API. |

---

## What This Service Does NOT Include

By design, this is a focused input-processing service:

- ❌ No LLM / TTS logic
- ❌ No Celery / task queues
- ❌ No WebSockets / streaming
- ❌ No authentication
- ❌ No database
