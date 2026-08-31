import os
import sys
import socket
import webbrowser
import threading
import time
import uvicorn

def is_port_available(port: int) -> bool:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.settimeout(0.5)
        return s.connect_ex(('127.0.0.1', port)) != 0

def find_available_port(start_port: int = 5000) -> int:
    port = start_port
    while port < start_port + 50:
        if is_port_available(port):
            return port
        port += 1
    return start_port

def open_browser(port: int):
    time.sleep(1.2)
    webbrowser.open(f"http://127.0.0.1:{port}")

def ensure_pot_server_async():
    def _worker():
        import urllib.request, subprocess
        try:
            with urllib.request.urlopen('http://127.0.0.1:4416/ping', timeout=0.5) as resp:
                if resp.status == 200:
                    return
        except Exception:
            pass
        
        server_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "desktop-app", "pot_provider", "server")
        main_js = os.path.join(server_dir, "build", "main.js")
        if os.path.exists(main_js):
            try:
                subprocess.Popen(
                    ["node", main_js, "--port", "4416"],
                    cwd=server_dir,
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                    creationflags=subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0
                )
            except Exception:
                pass
    threading.Thread(target=_worker, daemon=True).start()

def main():
    ensure_pot_server_async()
    port = find_available_port(5000)
    
    print("=" * 60)
    print("  KRONOS 4K • YouTube Video & Audio Downloader")
    print(f"  Server starting at: http://127.0.0.1:{port}")
    print("=" * 60)
    
    # Open browser automatically in background
    threading.Thread(target=open_browser, args=(port,), daemon=True).start()
    
    # Run FastAPI server with Uvicorn
    uvicorn.run("server:app", host="127.0.0.1", port=port, reload=False, log_level="info")


if __name__ == "__main__":
    main()
