<div align="center">

# ⚡ KRONOS 4K • YouTube Downloader

**A sleek, ultra-fast, modern YouTube video & audio downloader supporting up to 4K UHD 60FPS and 320kbps studio-grade audio extraction.**

[![Python](https://img.shields.io/badge/Python-3.10%2B-blue.svg?style=for-the-badge&logo=python&logoColor=white)](https://python.org)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.110%2B-009688.svg?style=for-the-badge&logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com)
[![yt-dlp](https://img.shields.io/badge/yt--dlp-Latest-red.svg?style=for-the-badge&logo=youtube&logoColor=white)](https://github.com/yt-dlp/yt-dlp)
[![FFmpeg](https://img.shields.io/badge/FFmpeg-8.x%20%2F%207.x-green.svg?style=for-the-badge&logo=ffmpeg&logoColor=white)](https://ffmpeg.org)
[![License](https://img.shields.io/badge/License-MIT-lightgrey.svg?style=for-the-badge)](LICENSE)

[Features](#-key-features) • [Prerequisites](#-prerequisites) • [Installation](#-installation) • [Quick Start](#-quick-start) • [Architecture](#-architecture) • [API Docs](#-api-endpoints)

</div>

---

## ✨ Key Features

- 🎬 **Ultra HD Video Support**: Download videos up to **4K UHD (2160p @ 60fps)**, **2K QHD (1440p)**, **1080p FHD**, **720p HD**, **480p**, and **360p**.
- 🎵 **Studio Audio Extraction**: Convert and export audio to **MP3 (Ultra HQ 320kbps & 192kbps)**, **Original M4A / AAC**, and **Lossless WAV** with embedded ID3 metadata tags.
- 🖤 **Luxury Monochrome UI**: Built with pure shades of black, obsidian glassmorphism, subtle glowing borders, and high-contrast typography.
- ⚡ **Instant Link Parsing**: Paste any YouTube link (or click *Paste from Clipboard*) to instantly fetch video metadata, thumbnails, duration, view counts, and stream sizes.
- 📊 **Real-Time Download Tracking**: Live progress bar showing download speed (MB/s), downloaded / total file size, estimated time remaining (ETA), and FFmpeg stream multiplexing status.
- 💾 **Direct Browser Downloads**: Triggers automatic browser file save once processing completes, with a one-click *"Reveal in File Explorer"* button.
- 🔒 **100% Private & Ad-Free**: Runs entirely on your local machine. No tracking, no third-party spam servers, no ads.

---

## 🛠️ Tech Stack

| Layer | Technology |
| :--- | :--- |
| **Backend** | [FastAPI](https://fastapi.tiangolo.com), [Uvicorn](https://www.uvicorn.org), [yt-dlp](https://github.com/yt-dlp/yt-dlp) |
| **Media Processing** | [FFmpeg](https://ffmpeg.org) (Stream merging, audio transcoding, ID3 tagger) |
| **Frontend** | Semantic HTML5, Vanilla CSS3 (Custom Design System, Glassmorphism, Micro-animations) |
| **Client Script** | Vanilla JavaScript (ES6+, Async Fetch, Live Polling, Clipboard API) |
| **Fonts** | Plus Jakarta Sans & JetBrains Mono |

---

## 📋 Prerequisites

Before running the application, ensure you have the following installed:

1. **Python 3.10+** (tested on Python 3.11 & 3.12)
   - Download from [python.org](https://www.python.org/downloads/)
2. **FFmpeg** (required for 4K video + audio merging and MP3 conversion)
   - **Windows**: Install via `winget install Gyan.FFmpeg` or `choco install ffmpeg`, or download from [gyan.dev](https://www.gyan.dev/ffmpeg/builds/) and add the `bin` folder to your System `PATH`.
   - **macOS**: `brew install ffmpeg`
   - **Linux (Ubuntu/Debian)**: `sudo apt update && sudo apt install ffmpeg`

Verify FFmpeg installation:
```bash
ffmpeg -version
```

---

## 🚀 Installation & Setup

### 1. Clone the Repository
```bash
git clone https://github.com/your-username/yt-downloader.git
cd yt-downloader
```

### 2. Install Python Dependencies
```bash
pip install -r requirements.txt
```

---

## 💻 Quick Start Options

### Option 1: Standalone Desktop App (.exe) • Easiest for Friends
Directly double-click the portable standalone executable:
```text
desktop-app/dist/Kronos4K.exe
```
*(No Python or FFmpeg installation required on other computers!)*

### Option 2: Local Web App (FastAPI + Browser)
Double-click **`start.bat`** or run:
```bash
python run.py
```
This opens `http://127.0.0.1:5000` in your default browser.

---

## 🎯 How to Use

1. **Copy a YouTube URL** from your browser or mobile app.
2. Click the **"Paste"** button or press <kbd>Ctrl</kbd> + <kbd>V</kbd> into the search input.
3. Click **"Fetch Video"** or press <kbd>Enter</kbd>.
4. Review the video preview card (Thumbnail, Title, Duration, Views, Channel).
5. Choose your desired format:
   - **Video Formats Tab**: Select **4K (2160p)**, 1440p, 1080p 60fps, 720p, etc.
   - **Audio Extraction Tab**: Select **MP3 320kbps**, 192kbps, M4A AAC, or WAV.
6. The live progress modal will track the download and FFmpeg stream multiplexing in real time.
7. Once finished, your browser will immediately download the file!

---

## 📁 Project Structure

```text
YT-Downloader/
├── static/
│   ├── index.html        # Clean, accessible UI layout
│   ├── style.css         # Modern monochrome design system & glassmorphism
│   └── app.js            # Video fetcher, live polling & download triggers
├── downloads/            # Local temporary cache for processed media files
├── downloader.py         # yt-dlp core wrapper, format parser & background workers
├── server.py             # FastAPI REST endpoints & static file serving
├── run.py                # Server launcher with auto-browser launcher
├── start.bat             # 1-click Windows batch runner
├── requirements.txt      # Python dependencies
└── README.md             # Documentation
```

---

## 🔌 API Endpoints

The backend provides a clean RESTful API:

| Method | Endpoint | Description | Payload / Parameters |
| :--- | :--- | :--- | :--- |
| `POST` | `/api/info` | Extracts video metadata, available resolutions, and audio options | `{ "url": "https://youtu.be/..." }` |
| `POST` | `/api/download` | Initiates an asynchronous background download task | `{ "url": "...", "option_id": "video_2160", "option_type": "video" }` |
| `GET` | `/api/progress/{task_id}` | Returns real-time download status, %, speed, and ETA | Path parameter: `task_id` |
| `GET` | `/api/file/{task_id}` | Streams the completed file directly to the browser | Path parameter: `task_id` |
| `POST` | `/api/open-folder/{task_id}` | Highlights the downloaded file in Windows File Explorer | Path parameter: `task_id` |

---

## 🛡️ Disclaimer

This software is intended for personal and educational use only. Please respect the copyright and terms of service of content owners. The authors are not responsible for any misuse of this tool.

---

## 📄 License

This project is licensed under the [MIT License](LICENSE) - feel free to use, modify, and distribute it.

<div align="center">
  <sub>Built with ❤️ using FastAPI, yt-dlp, and FFmpeg.</sub>
</div>
