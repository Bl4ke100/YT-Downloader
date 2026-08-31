import os
import sys
import re
import json
import zipfile
import shutil
import urllib.request
import importlib

def get_engine_dir() -> str:
    appdata = os.environ.get("APPDATA")
    if appdata:
        base_dir = os.path.join(appdata, "Kronos4K", "engine_updates")
    else:
        base_dir = os.path.join(os.path.expanduser("~"), ".kronos4k", "engine_updates")
    os.makedirs(base_dir, exist_ok=True)
    return base_dir

def ensure_engine_path():
    engine_dir = get_engine_dir()
    if engine_dir not in sys.path:
        sys.path.insert(0, engine_dir)

def normalize_version(ver_str: str) -> tuple:
    try:
        parts = [int(x) for x in re.findall(r'\d+', str(ver_str))]
        return tuple(parts) if parts else (0,)
    except Exception:
        return (0,)

def is_newer_version(latest: str, current: str) -> bool:
    return normalize_version(latest) > normalize_version(current)

def get_current_engine_version() -> str:
    try:
        ensure_engine_path()
        import yt_dlp
        return getattr(yt_dlp.version, "__version__", "unknown")
    except Exception:
        return "unknown"

def check_engine_update() -> dict:
    current_ver = get_current_engine_version()
    try:
        req = urllib.request.Request(
            "https://pypi.org/pypi/yt-dlp/json",
            headers={"User-Agent": "Kronos4K-Downloader/1.0"}
        )
        with urllib.request.urlopen(req, timeout=8) as response:
            data = json.loads(response.read().decode("utf-8"))
        
        info = data.get("info", {})
        latest_ver = info.get("version", current_ver)
        
        # Check if latest version is newer
        update_available = is_newer_version(latest_ver, current_ver)
        
        return {
            "success": True,
            "current_version": current_ver,
            "latest_version": latest_ver,
            "update_available": update_available,
            "release_url": info.get("release_url", "https://github.com/yt-dlp/yt-dlp/releases"),
            "summary": info.get("summary", "YouTube Downloader Engine")
        }
    except Exception as e:
        return {
            "success": False,
            "current_version": current_ver,
            "latest_version": current_ver,
            "update_available": False,
            "error": str(e)
        }

def install_engine_update() -> dict:
    ensure_engine_path()
    engine_dir = get_engine_dir()
    
    try:
        req = urllib.request.Request(
            "https://pypi.org/pypi/yt-dlp/json",
            headers={"User-Agent": "Kronos4K-Downloader/1.0"}
        )
        with urllib.request.urlopen(req, timeout=10) as response:
            data = json.loads(response.read().decode("utf-8"))
        
        urls = data.get("urls", [])
        wheel_url = None
        for u in urls:
            if u.get("filename", "").endswith("-py2.py3-none-any.whl") or u.get("filename", "").endswith(".whl"):
                wheel_url = u.get("url")
                break
        
        if not wheel_url:
            return {"success": False, "error": "No suitable pure-Python wheel found on PyPI."}
        
        temp_whl = os.path.join(engine_dir, "yt_dlp_update.zip")
        req_whl = urllib.request.Request(wheel_url, headers={"User-Agent": "Kronos4K-Downloader/1.0"})
        with urllib.request.urlopen(req_whl, timeout=30) as resp, open(temp_whl, "wb") as out_file:
            shutil.copyfileobj(resp, out_file)
        
        # Extract only yt_dlp package
        target_package_dir = os.path.join(engine_dir, "yt_dlp")
        if os.path.exists(target_package_dir):
            try:
                shutil.rmtree(target_package_dir)
            except Exception:
                pass
        
        with zipfile.ZipFile(temp_whl, "r") as zf:
            for member in zf.namelist():
                if member.startswith("yt_dlp/"):
                    zf.extract(member, engine_dir)
        
        if os.path.exists(temp_whl):
            try:
                os.remove(temp_whl)
            except Exception:
                pass
        
        importlib.invalidate_caches()
        
        # Reload or import yt_dlp
        if "yt_dlp" in sys.modules:
            try:
                import yt_dlp
                importlib.reload(yt_dlp)
            except Exception:
                pass
        
        new_ver = get_current_engine_version()
        return {
            "success": True,
            "message": f"Engine updated successfully to v{new_ver}!",
            "installed_version": new_ver
        }
    except Exception as e:
        return {"success": False, "error": str(e)}
