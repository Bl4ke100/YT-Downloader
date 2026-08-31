import os
import sys
import webbrowser
import threading
import time
import uvicorn

def open_browser():
    time.sleep(1.2)
    webbrowser.open("http://127.0.0.1:5000")

def main():
    print("=" * 60)
    print("  KRONOS 4K • YouTube Video & Audio Downloader")
    print("  Server starting at: http://127.0.0.1:5000")
    print("=" * 60)
    
    # Open browser automatically in background
    threading.Thread(target=open_browser, daemon=True).start()
    
    # Run FastAPI server with Uvicorn
    uvicorn.run("server:app", host="127.0.0.1", port=5000, reload=False, log_level="info")

if __name__ == "__main__":
    main()
