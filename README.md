<div align="center">

<img src="static/logo.png" alt="KRONOS 4K" width="90" />

# KRONOS 4K — YouTube Downloader

**A sleek, ultra-fast, privacy-first YouTube video & audio downloader.**
**Supports up to 4K UHD 60FPS, studio-grade 320kbps audio, and comes as a standalone desktop app — no installation required.**

[![Python](https://img.shields.io/badge/Python-3.10%2B-blue.svg?style=for-the-badge&logo=python&logoColor=white)](https://python.org)
[![FastAPI](https://img.shields.io/badge/FastAPI-Latest-009688.svg?style=for-the-badge&logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com)
[![yt-dlp](https://img.shields.io/badge/yt--dlp-Latest-red.svg?style=for-the-badge&logo=youtube&logoColor=white)](https://github.com/yt-dlp/yt-dlp)
[![FFmpeg](https://img.shields.io/badge/FFmpeg-8.x-green.svg?style=for-the-badge&logo=ffmpeg&logoColor=white)](https://ffmpeg.org)
[![License](https://img.shields.io/badge/License-MIT-lightgrey.svg?style=for-the-badge)](LICENSE)

[Features](#-features) • [Quick Start](#-quick-start) • [Desktop App](#-standalone-desktop-app) • [Web App](#-web-app) • [API](#-api-reference) • [Author](#-author)

</div>

---

## ✨ Features

| Feature | Details |
|---|---|
| 🎬 **4K UHD Video** | Download up to 2160p @ 60FPS with FFmpeg stream muxing |
| 🎵 **Studio Audio** | MP3 320kbps / 192kbps, M4A AAC, Lossless WAV with ID3 tags |
| ⏸️ **Download Controls** | Pause, Resume & Stop downloads mid-flight |
| ⚡ **1-Click Engine Updates** | Update yt-dlp without reinstalling the app |
| 🔑 **YouTube Authentication** | In-app YouTube login for age-restricted / private content |
| 🍪 **Cookie Import** | Import cookies from Chrome, Firefox, Edge, Brave, or upload a file |
| 🚀 **Standalone EXE** | Zero-dependency desktop app — share a single `.exe` with anyone |
| 🖥️ **Dual Mode** | Runs as a native desktop app (pywebview) OR a local web app |
| 🌐 **Real-Time Progress** | Live progress bar with speed, ETA, and file size |
| 🔒 **100% Private** | Everything runs locally — no tracking, no ads, no cloud |

---

## 🚀 Quick Start

### Option A — Standalone Desktop App (Recommended)

> No Python or FFmpeg installation needed. Just download and run.

1. Download **`Kronos4K.exe`** from [Releases](https://github.com/Bl4ke100/YT-Downloader/releases)
2. Double-click it — that's it!

---

### Option B — Web App (Python required)

#### 1. Prerequisites

- **Python 3.10+** — [python.org](https://www.python.org/downloads/)
- **FFmpeg** — required for 4K muxing and audio conversion
  - **Windows**: `winget install Gyan.FFmpeg`
  - **macOS**: `brew install ffmpeg`
  - **Linux**: `sudo apt install ffmpeg`

#### 2. Clone & Install

```bash
git clone https://github.com/Bl4ke100/YT-Downloader.git
cd YT-Downloader
pip install -r requirements.txt
```

#### 3. Run

```bash
python run.py
```

Opens at **`http://127.0.0.1:5000`** automatically.

Or on Windows, just double-click **`start.bat`**.

---

## 🖥️ Standalone Desktop App

The desktop app is built with [pywebview](https://pywebview.app/) and bundles Python, FFmpeg, and all dependencies into a single `.exe`.

### Build from Source

```bash
cd desktop-app
python build_exe.py
# Output: desktop-app/dist/Kronos4K.exe
```

> **Requirements to build**: Python 3.11, PyInstaller, pywebview, FFmpeg binary in `desktop-app/`

---

## 📖 How to Use

1. **Paste** a YouTube URL into the input field (or click the Paste button)
2. Click **Fetch Video** — metadata, thumbnail, and all available formats load instantly
3. Switch between the **Video** and **Audio** tabs to pick your format:
   - Video: 4K (2160p), 1440p, 1080p 60FPS, 720p, 480p, 360p
   - Audio: MP3 320kbps, MP3 192kbps, M4A AAC, WAV Lossless
4. Click **Download** — a live modal shows real-time progress
5. Use **Pause / Resume / Stop** controls at any time during the download
6. Once complete, save to browser or reveal the file in Explorer

### Authentication (Age-Restricted Videos)

- **Sign in to YouTube**: Click the `Auth` button → log in inside the pop-up window
- **Import browser cookies**: Click `Cookies` → select your browser or upload a `cookies.txt`

### Engine Updates

Click the **`⚡ Engine`** button to check for and install the latest `yt-dlp` release without restarting or reinstalling the app.

---

## 📁 Project Structure

```
YT-Downloader/
├── static/              # Web app frontend (HTML, CSS, JS, logo)
├── desktop-app/         # Desktop app source
│   ├── ui/              # Desktop UI (HTML, CSS, JS)
│   ├── main.py          # pywebview entry point & desktop API
│   ├── downloader_core.py
│   ├── engine_updater.py
│   └── build_exe.py     # PyInstaller build script
├── downloader.py        # yt-dlp core wrapper & background workers
├── server.py            # FastAPI REST API
├── engine_updater.py    # In-app yt-dlp update system
├── run.py               # Web server launcher
├── start.bat            # 1-click Windows launcher
└── requirements.txt
```

---

## 🌐 API Reference

| Method | Endpoint | Description |
|---|---|---|
| `POST` | `/api/info` | Fetch video metadata & available formats |
| `POST` | `/api/download` | Start a background download task |
| `GET` | `/api/progress/{task_id}` | Poll download progress (%, speed, ETA) |
| `POST` | `/api/download/pause/{task_id}` | Pause an active download |
| `POST` | `/api/download/resume/{task_id}` | Resume a paused download |
| `POST` | `/api/download/stop/{task_id}` | Stop and clean up a download |
| `GET` | `/api/file/{task_id}` | Stream the completed file to browser |
| `GET` | `/api/engine/status` | Check current vs latest yt-dlp version |
| `POST` | `/api/engine/update` | Install the latest yt-dlp engine |
| `POST` | `/api/cookies/import-browser` | Import cookies from an installed browser |

---

## ⚠️ Disclaimer

This tool is intended for **personal and educational use only**.
Please respect copyright laws and the Terms of Service of content platforms.
The author is not responsible for any misuse of this software.

---

## 👤 Author

**Bl4ke100**

- GitHub: [@Bl4ke100](https://github.com/Bl4ke100)

---

## 📄 License

This project is licensed under the [MIT License](LICENSE).

<div align="center">
  <sub>Built with ❤️ using FastAPI, yt-dlp, pywebview, and FFmpeg.</sub>
</div>
