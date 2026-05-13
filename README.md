# TikTok AI Generator

Automated pipeline that generates TikTok-style videos with historical curiosities using local AI.

## How it works

1. **Script** — LM Studio (local OpenAI-compatible server) generates a short historical curiosity script in Spanish
2. **Image prompt** — LM Studio creates an optimized English prompt for image generation
3. **Image** — ComfyUI generates images using the prompt and an image generation workflow
4. **Audio** — Coqui TTS converts the script to speech
5. **Video** — MoviePy assembles the video with crossfade transitions, captions, and audio

## Requirements

- Python 3.11+
- [LM Studio](https://lmstudio.ai/) running at `http://127.0.0.1:1234` with an OpenAI-compatible model loaded
- [ComfyUI](https://github.com/comfyanonymous/ComfyUI) running at `http://127.0.0.1:8000`
- [ImageMagick](https://imagemagick.org/) (for MoviePy text rendering)
- NVIDIA GPU (optional, for faster TTS inference)

## Setup

```bash
# Create virtual environment
python -m venv venv
.\venv\Scripts\activate

# Install dependencies
pip install TTS moviepy openai requests
```

## Usage

```bash
python main.py
```

The pipeline will:
1. Generate a historical script
2. Generate image prompts
3. Generate images via ComfyUI
4. Generate audio narration via Coqui TTS
5. Produce a video with captions under `outputs/`

## Configuration

Edit `main.py` to adjust:
- `COMFYUI_OUTPUT` — path to ComfyUI's output directory
- Model names for LM Studio and Coqui TTS
- Video resolution, transitions, and caption styling

## Tech stack

- **LM Studio** — local LLM inference
- **ComfyUI** — AI image generation
- **Coqui TTS** — text-to-speech
- **MoviePy** — video editing
- **FFmpeg** — audio/video encoding
