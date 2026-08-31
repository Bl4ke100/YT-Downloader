import os
import sys
import re
import urllib.parse
import subprocess
from typing import Optional
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
import uvicorn

import downloader
import engine_updater

app = FastAPI(title="YouTube 4K Downloader API", version="1.2.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class VideoInfoRequest(BaseModel):
    url: str
    browser_cookie: Optional[str] = None

class DownloadRequest(BaseModel):
    url: str
    option_id: str
    option_type: str
    browser_cookie: Optional[str] = None

class CookiesSaveRequest(BaseModel):
    content: str

class BrowserImportRequest(BaseModel):
    browser_name: str

def safe_filename(name: str) -> str:
    """Removes invalid characters for Windows and HTTP headers."""
    # Replace colons with dashes and remove illegal characters
    clean = re.sub(r'[:]', ' - ', name)
    clean = re.sub(r'[\\/*?"<>|]', '', clean)
    clean = re.sub(r'\s+', ' ', clean).strip()
    return clean or "downloaded_media.mp4"

@app.post("/api/info")
async def get_video_info(req: VideoInfoRequest):
    url = req.url.strip()
    if not url:
        raise HTTPException(status_code=400, detail="Please enter a valid YouTube URL.")
    
    try:
        info = downloader.extract_video_info(url, browser_cookie=req.browser_cookie)
        return info
    except Exception as e:
        clean_err = downloader.strip_ansi(str(e))
        if "is not a valid URL" in clean_err or "Unsupported url" in clean_err:
            raise HTTPException(status_code=400, detail="Invalid YouTube URL. Please check the link and try again.")
        raise HTTPException(status_code=400, detail=clean_err)

@app.post("/api/download")
async def start_download(req: DownloadRequest):
    url = req.url.strip()
    if not url:
        raise HTTPException(status_code=400, detail="URL is required.")
    
    try:
        task_id = downloader.create_download_task(
            url, 
            req.option_id, 
            req.option_type, 
            browser_cookie=req.browser_cookie
        )
        return {"task_id": task_id}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to start download: {downloader.strip_ansi(str(e))}")

@app.get("/api/progress/{task_id}")
async def get_progress(task_id: str):
    task = downloader.download_tasks.get(task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found.")
    return {k: v for k, v in task.items() if not k.startswith("_")}

@app.post("/api/download/pause/{task_id}")
async def pause_download(task_id: str):
    ok = downloader.pause_download_task(task_id)
    if not ok:
        raise HTTPException(status_code=404, detail="Task not found or unable to pause.")
    return {"success": True, "message": "Download paused."}

@app.post("/api/download/resume/{task_id}")
async def resume_download(task_id: str):
    ok = downloader.resume_download_task(task_id)
    if not ok:
        raise HTTPException(status_code=404, detail="Task not found or unable to resume.")
    return {"success": True, "message": "Download resumed."}

@app.post("/api/download/stop/{task_id}")
async def stop_download(task_id: str):
    ok = downloader.stop_download_task(task_id)
    if not ok:
        raise HTTPException(status_code=404, detail="Task not found or unable to stop.")
    return {"success": True, "message": "Download stopped."}

@app.get("/api/file/{task_id}")
async def download_file(task_id: str):
    task = downloader.download_tasks.get(task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found.")
    
    if task.get("status") != "completed":
        raise HTTPException(status_code=400, detail="File is not ready for download yet.")
    
    filepath = task.get("filepath")
    if not filepath or not os.path.exists(filepath):
        raise HTTPException(status_code=404, detail="File does not exist on server.")
    
    raw_filename = task.get("filename", os.path.basename(filepath))
    clean_name = safe_filename(raw_filename)
    
    # Determine appropriate content type
    ext = os.path.splitext(clean_name)[1].lower()
    content_type = "video/mp4"
    if ext == ".mp3":
        content_type = "audio/mpeg"
    elif ext == ".m4a":
        content_type = "audio/mp4"
    elif ext == ".wav":
        content_type = "audio/wav"
    elif ext == ".webm":
        content_type = "video/webm"
    
    return FileResponse(
        path=filepath,
        filename=clean_name,
        media_type=content_type,
        content_disposition_type="attachment"
    )

@app.post("/api/open-folder/{task_id}")
async def open_folder(task_id: str):
    task = downloader.download_tasks.get(task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found.")
    
    filepath = task.get("filepath")
    if not filepath or not os.path.exists(filepath):
        downloads_dir = downloader.DOWNLOADS_DIR
        subprocess.run(f'explorer /select,"{downloads_dir}"', shell=True)
        return {"success": True, "message": "Opened downloads folder"}
    
    norm_path = os.path.normpath(filepath)
    subprocess.run(f'explorer /select,"{norm_path}"', shell=True)
    return {"success": True, "message": "Revealed in File Explorer"}

@app.get("/api/cookies/status")
async def get_cookies_status():
    return {"has_cookies": downloader.has_cookies_file()}

@app.post("/api/cookies/save")
async def save_cookies(req: CookiesSaveRequest):
    ok = downloader.save_custom_cookies(req.content)
    if not ok:
        raise HTTPException(status_code=500, detail="Failed to save cookies.")
    return {"success": True, "message": "Cookies saved successfully!"}

@app.post("/api/cookies/clear")
async def clear_cookies():
    downloader.clear_custom_cookies()
    return {"success": True, "message": "Cookies cleared."}

@app.post("/api/cookies/import")
async def import_browser_cookies(req: BrowserImportRequest):
    res = downloader.import_cookies_from_browser(req.browser_name)
    if not res.get("success"):
        raise HTTPException(status_code=400, detail=res.get("error", "Failed to import cookies."))
    return res

@app.post("/api/auth/login-window")
async def open_login_window():
    try:
        script_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "auth_window.py")
        subprocess.Popen([sys.executable, script_path])
        return {"success": True, "message": "Sign-in window launched."}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/engine/status")
async def get_engine_status():
    return engine_updater.check_engine_update()

@app.post("/api/engine/update")
async def perform_engine_update():
    res = engine_updater.install_engine_update()
    if not res.get("success"):
        raise HTTPException(status_code=500, detail=res.get("error", "Update failed."))
    return res



# Serve static frontend
static_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "static")
os.makedirs(static_dir, exist_ok=True)
app.mount("/", StaticFiles(directory=static_dir, html=True), name="static")

if __name__ == "__main__":
    uvicorn.run("server:app", host="127.0.0.1", port=5000, reload=True)
