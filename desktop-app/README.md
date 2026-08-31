# ⚡ KRONOS 4K - Standalone Desktop App

A standalone Windows desktop application for downloading YouTube videos in up to 4K UHD (2160p 60fps) and extracting studio-grade audio (MP3 320kbps, M4A, WAV).

## ✨ Features
- **Standalone Executable**: Runs without Python or FFmpeg installation. Everything is bundled inside `Kronos4K.exe`.
- **Custom Frameless Title Bar**: Modern dark window with native Minimize, Maximize, and Close buttons.
- **Save Location Picker**: Choose your download folder with a native Windows folder selector.
- **Embedded FFmpeg 8.1**: High-speed video stream multiplexing and audio transcoding.
- **Cookie & Age-Gate Authentication**: Easily download age-restricted and private videos.

## 🚀 How to Run

### Option 1: Run the Standalone `.exe` (Best for sharing)
Simply double-click:
```text
desktop-app/dist/Kronos4K.exe
```

### Option 2: Run in Python Development Mode
Double-click `run_desktop.bat` or run:
```bash
python main.py
```

## 🔨 How to Rebuild the `.exe`
If you ever edit the UI or downloader code, simply double-click `build_exe.bat` or run:
```bash
python build_exe.py
```
This generates an updated `dist/Kronos4K.exe`.
