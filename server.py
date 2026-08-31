import os
import subprocess
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
import uvicorn

import downloader

app = FastAPI(title="YouTube 4K Downloader API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class VideoInfoRequest(BaseModel):
    url: str

class DownloadRequest(BaseModel):
    url: str
    option_id: str
    option_type: str

@app.post("/api/info")
async def get_video_info(req: VideoInfoRequest):
    url = req.url.strip()
    if not url:
        raise HTTPException(status_code=400, detail="Please enter a valid YouTube URL.")
    
    try:
        info = downloader.extract_video_info(url)
        return info
    except Exception as e:
        err_msg = str(e)
        if "is not a valid URL" in err_msg or "Unsupported url" in err_msg:
            raise HTTPException(status_code=400, detail="Invalid YouTube URL. Please check the link and try again.")
        raise HTTPException(status_code=500, detail=f"Failed to fetch video: {err_msg}")

@app.post("/api/download")
async def start_download(req: DownloadRequest):
    url = req.url.strip()
    if not url:
        raise HTTPException(status_code=400, detail="URL is required.")
    
    try:
        task_id = downloader.create_download_task(url, req.option_id, req.option_type)
        return {"task_id": task_id}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to start download: {str(e)}")

@app.get("/api/progress/{task_id}")
async def get_progress(task_id: str):
    task = downloader.download_tasks.get(task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found.")
    return task

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
    
    filename = task.get("filename", os.path.basename(filepath))
    
    return FileResponse(
        path=filepath,
        filename=filename,
        media_type="application/octet-stream",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'}
    )

@app.post("/api/open-folder/{task_id}")
async def open_folder(task_id: str):
    task = downloader.download_tasks.get(task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found.")
    
    filepath = task.get("filepath")
    if not filepath or not os.path.exists(filepath):
        # Open downloads folder if specific file not found
        downloads_dir = downloader.DOWNLOADS_DIR
        subprocess.run(f'explorer /select,"{downloads_dir}"', shell=True)
        return {"success": True, "message": "Opened downloads folder"}
    
    # Highlight file in Windows explorer
    norm_path = os.path.normpath(filepath)
    subprocess.run(f'explorer /select,"{norm_path}"', shell=True)
    return {"success": True, "message": "Revealed in File Explorer"}

# Serve static frontend
static_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "static")
os.makedirs(static_dir, exist_ok=True)
app.mount("/", StaticFiles(directory=static_dir, html=True), name="static")

if __name__ == "__main__":
    uvicorn.run("server:app", host="127.0.0.1", port=5000, reload=True)
