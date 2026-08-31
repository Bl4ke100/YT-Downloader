import os
import sys
import re
import uuid
import time
import shutil
import threading
from pathlib import Path
from typing import Dict, Any, Optional

import engine_updater
engine_updater.ensure_engine_path()

import yt_dlp

def get_base_dir() -> str:
    if getattr(sys, 'frozen', False):
        return os.path.dirname(sys.executable)
    return os.path.dirname(os.path.abspath(__file__))

def get_default_downloads_dir() -> str:
    user_downloads = str(Path.home() / "Downloads")
    if os.path.exists(user_downloads):
        return user_downloads
    return os.path.join(get_base_dir(), "downloads")

def get_cookies_file_path() -> str:
    # 1. Check persistent AppData directory
    app_data = os.getenv('APPDATA') or str(Path.home())
    kronos_dir = os.path.join(app_data, 'Kronos4K')
    os.makedirs(kronos_dir, exist_ok=True)
    appdata_cookies = os.path.join(kronos_dir, "cookies.txt")
    
    # 2. Local cookies next to exe
    local_cookies = os.path.join(get_base_dir(), "cookies.txt")
    if os.path.exists(local_cookies) and os.path.getsize(local_cookies) > 0 and not os.path.exists(appdata_cookies):
        return local_cookies
    return appdata_cookies

COOKIES_FILE = get_cookies_file_path()

active_tasks: Dict[str, Dict[str, Any]] = {}

def strip_ansi(text: str) -> str:
    return re.sub(r'(\x1b\[|\033\[|\[)[\d;]*[a-zA-Z]?', '', text).strip()

def format_duration(seconds: Optional[int]) -> str:
    if not seconds:
        return "0:00"
    m, s = divmod(int(seconds), 60)
    h, m = divmod(m, 60)
    if h > 0:
        return f"{h}:{m:02d}:{s:02d}"
    return f"{m}:{s:02d}"

def format_size(bytes_val: Optional[float]) -> str:
    if not bytes_val or bytes_val <= 0:
        return "Calculating..."
    for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
        if bytes_val < 1024.0:
            return f"{bytes_val:.1f} {unit}"
        bytes_val /= 1024.0
    return f"{bytes_val:.1f} PB"

def format_views(count: Optional[int]) -> str:
    if not count:
        return "0 views"
    if count >= 1_000_000_000:
        return f"{count / 1_000_000_000:.1f}B views"
    if count >= 1_000_000:
        return f"{count / 1_000_000:.1f}M views"
    if count >= 1_000:
        return f"{count / 1_000:.1f}K views"
    return f"{count:,} views"

def get_base_ydl_opts(browser_cookie: Optional[str] = None) -> Dict[str, Any]:
    opts: Dict[str, Any] = {
        'quiet': True,
        'no_warnings': True,
        'remote_components': {'ejs:github'},
        'extractor_args': {
            'youtube': {
                'player_client': ['web_creator', 'web']
            }
        }
    }
    
    app_ffmpeg = os.path.join(get_base_dir(), "ffmpeg.exe")
    if os.path.exists(app_ffmpeg):
        opts['ffmpeg_location'] = app_ffmpeg
        
    if os.path.exists(COOKIES_FILE) and os.path.getsize(COOKIES_FILE) > 0:
        opts['cookiefile'] = COOKIES_FILE
    elif browser_cookie and browser_cookie.lower() != 'none':
        opts['cookiesfrombrowser'] = (browser_cookie.lower(), None, None, None)
        
    return opts

def extract_video_info(url: str, browser_cookie: Optional[str] = None) -> Dict[str, Any]:
    ydl_opts = get_base_ydl_opts(browser_cookie)
    ydl_opts.update({
        'skip_download': True,
        'extract_flat': False,
    })
    
    info = None
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False)
    except Exception as primary_err:
        err_str = strip_ansi(str(primary_err))
        
        # Handle Windows browser cookie locking (e.g. Chrome is running)
        if "Could not copy" in err_str or "cookie database" in err_str:
            try:
                fallback_opts = get_base_ydl_opts('none')
                fallback_opts.update({'skip_download': True, 'extract_flat': False})
                with yt_dlp.YoutubeDL(fallback_opts) as fallback_ydl:
                    info = fallback_ydl.extract_info(url, download=False)
            except Exception as fallback_err:
                fb_msg = strip_ansi(str(fallback_err))
                if "Sign in to confirm your age" in fb_msg or "cookies" in fb_msg.lower():
                    bname = browser_cookie.capitalize() if browser_cookie else "Your browser"
                    raise Exception(
                        f"{bname} is currently open, which locks its cookie database on Windows. "
                        "To download age-restricted videos without closing your browser, please upload or paste cookies.txt in Cookie Settings."
                    )
                raise Exception(fb_msg)
        elif "Sign in to confirm your age" in err_str or "cookies" in err_str.lower():
            raise Exception(
                "This video is age-restricted or requires sign-in. "
                "Please click the 'Cookies' button at the top to upload or paste your cookies.txt."
            )
        else:
            raise Exception(err_str)
        
    duration = info.get('duration', 0)
    formats = info.get('formats', [])
    
    best_audio_size = 0
    audio_formats = [f for f in formats if f.get('vcodec') == 'none' and f.get('acodec') != 'none']
    if audio_formats:
        best_audio = max(audio_formats, key=lambda f: f.get('abr', 0) or 0)
        best_audio_size = best_audio.get('filesize') or best_audio.get('filesize_approx') or 0
        if not best_audio_size and duration and best_audio.get('abr'):
            best_audio_size = int((best_audio.get('abr') * 1000 / 8) * duration)

    target_resolutions = [
        {"height": 4320, "label": "8K Ultra HD", "badge": "8K 4320p", "tag": "8K"},
        {"height": 2160, "label": "4K Ultra HD", "badge": "4K 2160p", "tag": "4K"},
        {"height": 1440, "label": "2K Quad HD", "badge": "2K 1440p", "tag": "2K"},
        {"height": 1080, "label": "1080p Full HD", "badge": "1080p FHD", "tag": "FHD"},
        {"height": 720,  "label": "720p HD", "badge": "720p HD", "tag": "HD"},
        {"height": 480,  "label": "480p Standard", "badge": "480p SD", "tag": "SD"},
        {"height": 360,  "label": "360p Basic", "badge": "360p", "tag": "SD"},
    ]

    video_options = []
    seen_heights = set()

    for target in target_resolutions:
        th = target["height"]
        matching_v_formats = [
            f for f in formats 
            if f.get('height') and abs(f.get('height') - th) <= 10 and f.get('vcodec') != 'none'
        ]
        
        if matching_v_formats and th not in seen_heights:
            seen_heights.add(th)
            best_f = max(
                matching_v_formats, 
                key=lambda x: (x.get('fps') or 30, x.get('tbr') or x.get('vbr') or 0)
            )
            fps = best_f.get('fps')
            fps_str = f"{fps}fps" if fps and fps > 30 else ""
            
            v_size = best_f.get('filesize') or best_f.get('filesize_approx') or 0
            if not v_size and duration and (best_f.get('tbr') or best_f.get('vbr')):
                bitrate = (best_f.get('tbr') or best_f.get('vbr')) * 1000 / 8
                v_size = int(bitrate * duration)
            
            total_size = v_size + (best_audio_size if best_f.get('acodec') == 'none' else 0)
            
            video_options.append({
                "id": f"video_{th}",
                "type": "video",
                "height": th,
                "label": target["label"],
                "badge": target["badge"],
                "fps": fps_str,
                "tag": target["tag"],
                "ext": "mp4",
                "format_id": best_f.get('format_id'),
                "size_formatted": format_size(total_size) if total_size > 0 else "Dynamic estimate",
                "estimated_bytes": total_size
            })

    audio_options = [
        {
            "id": "audio_mp3_320",
            "type": "audio",
            "format": "mp3",
            "quality": "320",
            "label": "MP3 Audio (Ultra HQ 320kbps)",
            "badge": "MP3 320k",
            "tag": "HQ",
            "size_formatted": format_size(int((320 * 1000 / 8) * duration)) if duration else "Dynamic",
            "ext": "mp3"
        },
        {
            "id": "audio_mp3_192",
            "type": "audio",
            "format": "mp3",
            "quality": "192",
            "label": "MP3 Audio (Standard 192kbps)",
            "badge": "MP3 192k",
            "tag": "MP3",
            "size_formatted": format_size(int((192 * 1000 / 8) * duration)) if duration else "Dynamic",
            "ext": "mp3"
        },
        {
            "id": "audio_m4a",
            "type": "audio",
            "format": "m4a",
            "quality": "best",
            "label": "M4A / AAC (Original Stream)",
            "badge": "M4A AAC",
            "tag": "AAC",
            "size_formatted": format_size(best_audio_size) if best_audio_size else "Dynamic",
            "ext": "m4a"
        },
        {
            "id": "audio_wav",
            "type": "audio",
            "format": "wav",
            "quality": "best",
            "label": "WAV Audio (Lossless Uncompressed)",
            "badge": "WAV",
            "tag": "WAV",
            "size_formatted": format_size(int((1411 * 1000 / 8) * duration)) if duration else "Dynamic",
            "ext": "wav"
        },
    ]

    thumbnails = info.get('thumbnails', [])
    thumbnail_url = info.get('thumbnail')
    if thumbnails:
        sorted_thumbs = sorted(thumbnails, key=lambda t: (t.get('width') or 0, t.get('height') or 0), reverse=True)
        thumbnail_url = sorted_thumbs[0].get('url') or thumbnail_url

    return {
        "id": info.get("id"),
        "url": url,
        "title": info.get("title", "Untitled Video"),
        "channel": info.get("uploader") or info.get("channel", "Unknown Channel"),
        "channel_url": info.get("uploader_url") or info.get("channel_url", ""),
        "duration": duration,
        "duration_formatted": format_duration(duration),
        "views": info.get("view_count", 0),
        "views_formatted": format_views(info.get("view_count")),
        "upload_date": info.get("upload_date", ""),
        "thumbnail": thumbnail_url,
        "video_options": video_options,
        "audio_options": audio_options
    }

def start_download_thread(task_id: str, url: str, option_id: str, option_type: str, save_dir: str, browser_cookie: Optional[str] = None):
    def hook(d):
        task = active_tasks.get(task_id)
        if not task:
            return
        
        # 1. Check for cancellation
        if task.get("_cancel_requested"):
            raise Exception("DOWNLOAD_STOPPED_BY_USER")
        
        # 2. Check for pause state
        pe = task.get("_pause_event")
        if pe and not pe.is_set():
            task.update({
                "status": "paused",
                "speed": "0 KB/s (Paused)",
                "step_message": "Download paused by user"
            })
            while pe and not pe.is_set():
                if task.get("_cancel_requested"):
                    raise Exception("DOWNLOAD_STOPPED_BY_USER")
                time.sleep(0.3)
            if task.get("status") == "paused":
                task["status"] = "downloading"

        status = d.get('status')
        if status == 'downloading':
            total_bytes = d.get('total_bytes') or d.get('total_bytes_estimate') or 0
            downloaded_bytes = d.get('downloaded_bytes') or 0
            
            percent = 0.0
            if total_bytes > 0:
                percent = round((downloaded_bytes / total_bytes) * 100, 1)
            elif d.get('_percent_str'):
                try:
                    clean_p = re.sub(r'[^\d.]', '', d.get('_percent_str', '0'))
                    percent = float(clean_p)
                except Exception:
                    pass
            
            speed = d.get('speed')
            speed_str = f"{format_size(speed)}/s" if speed else d.get('_speed_str', '')
            eta = d.get('eta')
            eta_str = f"{eta}s" if eta else d.get('_eta_str', '')
            
            task.update({
                "status": "downloading",
                "progress": min(percent, 98.0),
                "speed": speed_str,
                "eta": eta_str,
                "downloaded_bytes": downloaded_bytes,
                "total_bytes": total_bytes,
                "downloaded_formatted": format_size(downloaded_bytes),
                "total_formatted": format_size(total_bytes) if total_bytes else "Calculating...",
                "step_message": f"Downloading: {percent}% ({speed_str})"
            })
            
        elif status == 'finished':
            task.update({
                "status": "processing",
                "progress": 99.0,
                "step_message": "Merging streams & applying metadata..."
            })

    try:
        pause_event = threading.Event()
        pause_event.set()

        active_tasks[task_id] = {
            "task_id": task_id,
            "status": "starting",
            "progress": 0,
            "speed": "0 KB/s",
            "eta": "--",
            "step_message": "Connecting to streams...",
            "filename": None,
            "filepath": None,
            "filesize": 0,
            "error": None,
            "created_at": time.time(),
            "_pause_event": pause_event,
            "_cancel_requested": False
        }

        os.makedirs(save_dir, exist_ok=True)
        out_template = os.path.join(save_dir, "%(title).100s.%(ext)s")

        ydl_opts = get_base_ydl_opts(browser_cookie)
        ydl_opts.update({
            'outtmpl': out_template,
            'progress_hooks': [hook],
            'continuedl': True,
        })

        if option_type == 'audio':
            if option_id == "audio_mp3_320":
                ydl_opts.update({
                    'format': 'bestaudio/best',
                    'postprocessors': [{
                        'key': 'FFmpegExtractAudio',
                        'preferredcodec': 'mp3',
                        'preferredquality': '320',
                    }, {
                        'key': 'FFmpegMetadata',
                        'add_metadata': True,
                    }],
                })
            elif option_id == "audio_mp3_192":
                ydl_opts.update({
                    'format': 'bestaudio/best',
                    'postprocessors': [{
                        'key': 'FFmpegExtractAudio',
                        'preferredcodec': 'mp3',
                        'preferredquality': '192',
                    }, {
                        'key': 'FFmpegMetadata',
                        'add_metadata': True,
                    }],
                })
            elif option_id == "audio_m4a":
                ydl_opts.update({
                    'format': 'bestaudio[ext=m4a]/bestaudio/best',
                    'postprocessors': [{
                        'key': 'FFmpegExtractAudio',
                        'preferredcodec': 'm4a',
                    }, {
                        'key': 'FFmpegMetadata',
                        'add_metadata': True,
                    }],
                })
            elif option_id == "audio_wav":
                ydl_opts.update({
                    'format': 'bestaudio/best',
                    'postprocessors': [{
                        'key': 'FFmpegExtractAudio',
                        'preferredcodec': 'wav',
                    }],
                })
            else:
                ydl_opts.update({
                    'format': 'bestaudio/best',
                    'postprocessors': [{
                        'key': 'FFmpegExtractAudio',
                        'preferredcodec': 'mp3',
                        'preferredquality': '320',
                    }],
                })
        else:
            m = re.search(r'video_(\d+)', option_id)
            target_height = int(m.group(1)) if m else None
            
            if target_height:
                format_spec = (
                    f"bestvideo[height<={target_height}][ext=mp4]+bestaudio[ext=m4a]/"
                    f"bestvideo[height<={target_height}]+bestaudio/"
                    f"best[height<={target_height}]/best"
                )
            else:
                format_spec = "bestvideo[ext=mp4]+bestaudio[ext=m4a]/bestvideo+bestaudio/best"

            ydl_opts.update({
                'format': format_spec,
                'merge_output_format': 'mp4',
                'postprocessors': [{
                    'key': 'FFmpegMetadata',
                    'add_metadata': True,
                }],
            })

        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                res = ydl.extract_info(url, download=True)
        except Exception as dl_err:
            dl_err_str = strip_ansi(str(dl_err))
            if "Could not copy" in dl_err_str or "cookie database" in dl_err_str:
                # Retry download without locked browser cookie
                fallback_dl_opts = dict(ydl_opts)
                fallback_dl_opts.pop('cookiesfrombrowser', None)
                with yt_dlp.YoutubeDL(fallback_dl_opts) as fallback_ydl:
                    res = fallback_ydl.extract_info(url, download=True)
            else:
                raise dl_err
            
        found_filepath = None
        if 'requested_downloads' in res and res['requested_downloads']:
            found_filepath = res['requested_downloads'][0].get('filepath')
        
        if not found_filepath or not os.path.exists(found_filepath):
            for fname in os.listdir(save_dir):
                fpath = os.path.join(save_dir, fname)
                if os.path.isfile(fpath) and (time.time() - os.path.getmtime(fpath) < 60):
                    found_filepath = fpath
                    break
            
        if found_filepath and os.path.exists(found_filepath):
            actual_filename = os.path.basename(found_filepath)
            filesize = os.path.getsize(found_filepath)
            
            active_tasks[task_id].update({
                "status": "completed",
                "progress": 100.0,
                "filepath": found_filepath,
                "filename": actual_filename,
                "filesize": filesize,
                "filesize_formatted": format_size(filesize),
                "step_message": "Saved directly to folder!"
            })
        else:
            active_tasks[task_id].update({
                "status": "error",
                "error": "Could not locate completed output file."
            })

    except Exception as e:
        err_clean = strip_ansi(str(e))
        if "DOWNLOAD_STOPPED_BY_USER" in err_clean:
            active_tasks[task_id].update({
                "status": "stopped",
                "speed": "0 KB/s",
                "eta": "--",
                "step_message": "Download stopped by user."
            })
            # Clean up partial files
            try:
                for fname in os.listdir(save_dir):
                    if fname.endswith(".part") or fname.endswith(".ytdl"):
                        try:
                            os.remove(os.path.join(save_dir, fname))
                        except Exception:
                            pass
            except Exception:
                pass
            return
        
        active_tasks[task_id].update({
            "status": "error",
            "error": err_clean,
            "step_message": f"Error: {err_clean}"
        })

def pause_download_task(task_id: str) -> bool:
    task = active_tasks.get(task_id)
    if not task:
        return False
    pe = task.get("_pause_event")
    if pe:
        pe.clear()
        task["status"] = "paused"
        task["speed"] = "0 KB/s (Paused)"
        task["step_message"] = "Download paused by user."
        return True
    return False

def resume_download_task(task_id: str) -> bool:
    task = active_tasks.get(task_id)
    if not task:
        return False
    pe = task.get("_pause_event")
    if pe:
        pe.set()
        task["status"] = "downloading"
        task["step_message"] = "Resuming download..."
        return True
    return False

def stop_download_task(task_id: str) -> bool:
    task = active_tasks.get(task_id)
    if not task:
        return False
    task["_cancel_requested"] = True
    pe = task.get("_pause_event")
    if pe:
        pe.set() # Unblock pause wait so thread exits immediately
    task["status"] = "stopped"
    task["step_message"] = "Stopping download..."
    return True

def create_download_task(url: str, option_id: str, option_type: str, save_dir: str, browser_cookie: Optional[str] = None) -> str:
    task_id = str(uuid.uuid4())[:8]
    thread = threading.Thread(
        target=start_download_thread,
        args=(task_id, url, option_id, option_type, save_dir, browser_cookie),
        daemon=True
    )
    thread.start()
    return task_id

def save_custom_cookies(cookie_content: str) -> bool:
    try:
        with open(COOKIES_FILE, "w", encoding="utf-8") as f:
            f.write(cookie_content.strip())
        return True
    except Exception:
        return False

def clear_custom_cookies() -> bool:
    try:
        if os.path.exists(COOKIES_FILE):
            os.remove(COOKIES_FILE)
        return True
    except Exception:
        return False

def has_cookies_file() -> bool:
    return os.path.exists(COOKIES_FILE) and os.path.getsize(COOKIES_FILE) > 0

def import_cookies_from_browser(browser_name: str) -> Dict[str, Any]:
    try:
        browser_key = browser_name.lower().strip()
        ydl_opts = {
            'cookiesfrombrowser': (browser_key, None, None, None),
            'quiet': True,
            'no_warnings': True
        }
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            jar = ydl.cookiejar
            cookie_count = len(jar)
            if cookie_count == 0:
                return {
                    "success": False,
                    "error": f"No cookies found in {browser_name.title()}. Make sure you are logged into YouTube in that browser."
                }
            
            lines = [
                "# Netscape HTTP Cookie File",
                f"# Exported from {browser_name.title()} by KRONOS 4K",
                ""
            ]
            for cookie in jar:
                domain = cookie.domain
                flag = "TRUE" if domain.startswith('.') else "FALSE"
                path = cookie.path or '/'
                secure = "TRUE" if cookie.secure else "FALSE"
                exp = str(int(cookie.expires)) if cookie.expires else str(int(time.time() + 86400 * 365))
                lines.append(f"{domain}\t{flag}\t{path}\t{secure}\t{exp}\t{cookie.name}\t{cookie.value}")
            
            content = "\n".join(lines)
            save_custom_cookies(content)
            
            return {
                "success": True,
                "message": f"Successfully imported {cookie_count} cookies from {browser_name.title()}!",
                "cookie_count": cookie_count
            }
    except Exception as e:
        err_msg = str(e)
        if "Could not copy" in err_msg or "cookie database" in err_msg:
            return {
                "success": False,
                "error": f"Could not read {browser_name.title()} cookies because {browser_name.title()} is currently open. Please close {browser_name.title()} temporarily and click Import, or use the 1-Click In-App Sign-In."
            }
        return {
            "success": False,
            "error": f"Failed to import from {browser_name.title()}: {err_msg}"
        }

