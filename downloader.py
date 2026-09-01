import os
import sys
import re
import math
import uuid
import time
import subprocess
import threading
from typing import Dict, Any, Optional

import engine_updater
engine_updater.ensure_engine_path()

import yt_dlp

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DOWNLOADS_DIR = os.path.join(BASE_DIR, "downloads")

def get_cookies_file_path() -> str:
    app_data = os.getenv('APPDATA') or os.path.expanduser('~')
    kronos_dir = os.path.join(app_data, 'Kronos4K')
    os.makedirs(kronos_dir, exist_ok=True)
    appdata_cookies = os.path.join(kronos_dir, "cookies.txt")
    
    local_cookies = os.path.join(BASE_DIR, "cookies.txt")
    if os.path.exists(local_cookies) and os.path.getsize(local_cookies) > 0 and not os.path.exists(appdata_cookies):
        return local_cookies
    return appdata_cookies

COOKIES_FILE = get_cookies_file_path()
os.makedirs(DOWNLOADS_DIR, exist_ok=True)

# In-memory store for download task progress
download_tasks: Dict[str, Dict[str, Any]] = {}

def get_ffmpeg_executable() -> str:
    local_ffmpeg = os.path.join(BASE_DIR, "ffmpeg.exe")
    if os.path.exists(local_ffmpeg):
        return local_ffmpeg
    return "ffmpeg"

def get_media_codecs(filepath: str) -> Dict[str, Optional[str]]:
    ffmpeg_exe = get_ffmpeg_executable()
    try:
        cmd = [ffmpeg_exe, "-i", filepath]
        res = subprocess.run(cmd, capture_output=True, text=True, errors="replace")
        output = res.stderr
        
        vcodec = None
        acodec = None
        pix_fmt = None
        
        for line in output.splitlines():
            if "Stream #" in line:
                if "Video:" in line and not vcodec:
                    m = re.search(r'Video:\s*([a-zA-Z0-9_-]+)', line)
                    if m:
                        vcodec = m.group(1).lower()
                    m_pix = re.search(r',\s*([a-zA-Z0-9]+)(\(|$|,|\s)', line)
                    if m_pix:
                        pix_fmt = m_pix.group(1).lower()
                elif "Audio:" in line and not acodec:
                    m = re.search(r'Audio:\s*([a-zA-Z0-9_-]+)', line)
                    if m:
                        acodec = m.group(1).lower()
                        
        return {"vcodec": vcodec, "acodec": acodec, "pix_fmt": pix_fmt}
    except Exception:
        return {"vcodec": None, "acodec": None, "pix_fmt": None}

def ensure_nle_compatible(filepath: str, task_id: Optional[str] = None) -> str:
    """
    Ensures the downloaded MP4 is 100% compatible with Adobe After Effects, Premiere Pro,
    DaVinci Resolve, Shutter Encoder, QuickTime, and Windows Media Player by transcoding 
    non-standard VP9/AV1/Opus streams into H.264 High Profile (AVC) + AAC Stereo + yuv420p.
    """
    if not filepath or not os.path.exists(filepath):
        return filepath
        
    _, ext = os.path.splitext(filepath)
    if ext.lower() not in ['.mp4', '.mkv', '.webm', '.mov']:
        return filepath
        
    ffmpeg_exe = get_ffmpeg_executable()
    info = get_media_codecs(filepath)
    vcodec = (info.get("vcodec") or "").lower()
    acodec = (info.get("acodec") or "").lower()
    pix_fmt = (info.get("pix_fmt") or "").lower()
    
    # Check if already 100% standard NLE-compatible
    is_v_h264 = ("h264" in vcodec or "avc" in vcodec)
    is_a_aac = ("aac" in acodec or "mp4a" in acodec)
    is_pix_standard = pix_fmt in ["yuv420p", "nv12"]
    
    if is_v_h264 and is_a_aac and is_pix_standard:
        return filepath
        
    if task_id and task_id in download_tasks:
        download_tasks[task_id].update({
            "step_message": "Optimizing for After Effects & Premiere Pro (H.264)..."
        })
        
    dir_name, base_name = os.path.split(filepath)
    name_no_ext, _ = os.path.splitext(base_name)
    temp_output = os.path.join(dir_name, f"kronos_ae_{int(time.time())}_{name_no_ext}.mp4")
    
    # Case 1: Video is already H.264/AVC, but audio or container needs AAC / faststart
    if is_v_h264 and is_pix_standard:
        cmd = [
            ffmpeg_exe, "-y", "-i", filepath,
            "-c:v", "copy",
            "-c:a", "aac", "-b:a", "320k",
            "-movflags", "+faststart",
            temp_output
        ]
        try:
            res = subprocess.run(cmd, capture_output=True, text=True, errors="replace")
            if res.returncode == 0 and os.path.exists(temp_output) and os.path.getsize(temp_output) > 1000:
                os.replace(temp_output, filepath)
                return filepath
        except Exception:
            pass
        if os.path.exists(temp_output):
            try:
                os.remove(temp_output)
            except Exception:
                pass
        return filepath
        
    # Case 2: Video is VP9 / AV1 (e.g. 1440p / 4K from YouTube)
    # Try Hardware Encoders for ultra-fast speed, falling back to multi-threaded libx264
    encoders_to_try = [
        ["-c:v", "h264_nvenc", "-preset", "p5", "-cq", "18"],
        ["-c:v", "h264_qsv", "-global_quality", "18"],
        ["-c:v", "h264_amf", "-rc", "cbr", "-quality", "speed"],
        ["-c:v", "libx264", "-preset", "veryfast", "-crf", "18", "-threads", "0"]
    ]
    
    for enc_args in encoders_to_try:
        cmd = [
            ffmpeg_exe, "-y", "-i", filepath,
            *enc_args,
            "-pix_fmt", "yuv420p",
            "-c:a", "aac", "-b:a", "320k",
            "-movflags", "+faststart",
            temp_output
        ]
        try:
            res = subprocess.run(cmd, capture_output=True, text=True, errors="replace")
            if res.returncode == 0 and os.path.exists(temp_output) and os.path.getsize(temp_output) > 1000:
                # Transcode succeeded! Replace original file with the 100% NLE-ready MP4
                os.replace(temp_output, filepath)
                return filepath
        except Exception:
            pass
            
        if os.path.exists(temp_output):
            try:
                os.remove(temp_output)
            except Exception:
                pass
                
    return filepath

def strip_ansi(text: str) -> str:
    """Removes ANSI color and formatting codes from strings."""
    return re.sub(r'(\x1b\[|\033\[|\[)[\d;]*[a-zA-Z]?', '', text).strip()

def format_duration(seconds: Optional[int]) -> str:
    if not seconds:
        return "0:00"
    m, s = divmod(seconds, 60)
    h, m = divmod(m, 60)
    if h > 0:
        return f"{h}:{m:02d}:{s:02d}"
    return f"{m}:{s:02d}"

def format_size(bytes_val: Optional[float]) -> str:
    if not bytes_val or bytes_val <= 0:
        return "Unknown"
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
    
    app_ffmpeg = get_ffmpeg_executable()
    if app_ffmpeg and os.path.exists(app_ffmpeg):
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
        if "Could not copy" in err_str or "cookie database" in err_str:
            fallback_opts = dict(ydl_opts)
            fallback_opts.pop('cookiesfrombrowser', None)
            with yt_dlp.YoutubeDL(fallback_opts) as fallback_ydl:
                info = fallback_ydl.extract_info(url, download=False)
        else:
            raise primary_err

    if not info:
        raise ValueError("Could not extract video metadata from this URL.")

    formats = info.get("formats", [])
    duration = info.get("duration")

    standard_resolutions = [
        (2160, "4K UHD (2160p 60fps)", "4K UHD", "video_2160"),
        (1440, "2K QHD (1440p 60fps)", "1440p", "video_1440"),
        (1080, "Full HD (1080p 60fps)", "1080p", "video_1080"),
        (720, "HD (720p 60fps)", "720p", "video_720"),
        (480, "Standard (480p)", "480p", "video_480"),
        (360, "Low (360p)", "360p", "video_360")
    ]

    best_audio_size = 0
    for f in formats:
        if f.get("acodec") != "none" and f.get("vcodec") == "none":
            s = f.get("filesize") or f.get("filesize_approx") or 0
            if s > best_audio_size:
                best_audio_size = s

    if not best_audio_size and duration:
        best_audio_size = int((128 * 1000 / 8) * duration)

    video_options = []
    max_height_found = max((f.get("height") or 0 for f in formats), default=0)

    for target_height, label, badge, opt_id in standard_resolutions:
        matching_video_formats = [
            f for f in formats 
            if f.get("height") == target_height
            and f.get("vcodec") != "none"
        ]
        
        has_this_res = bool(matching_video_formats) or (max_height_found >= target_height)

        if has_this_res:
            calc_size = 0
            best_fps = 30
            for f in matching_video_formats:
                s = f.get("filesize") or f.get("filesize_approx") or 0
                if s > calc_size:
                    calc_size = s
                fps_val = f.get("fps") or 30
                if fps_val > best_fps:
                    best_fps = int(fps_val)
                    
            if calc_size:
                total_size = calc_size + best_audio_size
                formatted_size = format_size(total_size)
            elif duration:
                bitrates = {2160: 25000, 1440: 12000, 1080: 4500, 720: 2500, 480: 1200, 360: 700}
                est_bytes = int(((bitrates.get(target_height, 2000) + 128) * 1000 / 8) * duration)
                formatted_size = format_size(est_bytes)
            else:
                formatted_size = "Dynamic Stream"

            fps_suffix = f" {best_fps}fps" if best_fps > 30 else ""
            display_label = label.replace("60fps", f"{best_fps}fps") if "60fps" in label else f"{label}{fps_suffix}"

            video_options.append({
                "id": opt_id,
                "type": "video",
                "quality": f"{target_height}p",
                "label": display_label,
                "badge": badge,
                "tag": f"{target_height}P",
                "size_formatted": formatted_size,
                "ext": "mp4"
            })

    audio_options = [
        {
            "id": "audio_mp3_320",
            "type": "audio",
            "format": "mp3",
            "quality": "320",
            "label": "MP3 Audio (Studio Master 320kbps)",
            "badge": "MP3 320k",
            "tag": "MP3 HQ",
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

    thumbnail_url = info.get("thumbnail")
    thumbnails = info.get("thumbnails", [])
    if thumbnails:
        thumbnail_url = thumbnails[-1].get("url") or thumbnail_url

    return {
        "id": info.get("id"),
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
        "audio_options": audio_options,
    }

def start_download_thread(task_id: str, url: str, option_id: str, option_type: str, browser_cookie: Optional[str] = None):
    try:
        pause_event = threading.Event()
        pause_event.set()

        download_tasks[task_id] = {
            "task_id": task_id,
            "status": "starting",
            "progress": 0.0,
            "speed": "0 KB/s",
            "eta": "--",
            "downloaded_bytes": 0,
            "total_bytes": 0,
            "downloaded_formatted": "0 MB",
            "total_formatted": "Calculating...",
            "filepath": None,
            "filename": None,
            "filesize": 0,
            "filesize_formatted": "0 MB",
            "error": None,
            "step_message": "Initializing download streams...",
            "_pause_event": pause_event,
            "_cancel_requested": False
        }

        def hook(d):
            if download_tasks.get(task_id, {}).get("_cancel_requested", False):
                raise Exception("DOWNLOAD_STOPPED_BY_USER")

            pe = download_tasks.get(task_id, {}).get("_pause_event")
            if pe and not pe.is_set():
                download_tasks[task_id]["status"] = "paused"
                download_tasks[task_id]["speed"] = "0 KB/s (Paused)"
                download_tasks[task_id]["step_message"] = "Download paused by user"
                while pe and not pe.is_set():
                    if download_tasks.get(task_id, {}).get("_cancel_requested", False):
                        raise Exception("DOWNLOAD_STOPPED_BY_USER")
                    time.sleep(0.3)
                if download_tasks.get(task_id, {}).get("status") == "paused":
                    download_tasks[task_id]["status"] = "downloading"

            if d.get('status') != 'downloading':
                if d.get('status') == 'finished':
                    download_tasks[task_id].update({
                        "progress": 100.0,
                        "step_message": "Finalizing & optimizing for editing..."
                    })
                return

            downloaded_bytes = d.get('downloaded_bytes', 0)
            total_bytes = d.get('total_bytes') or d.get('total_bytes_estimate') or 0
            
            percent = 0.0
            if total_bytes > 0:
                percent = round((downloaded_bytes / total_bytes) * 100.0, 1)
            else:
                p_str = strip_ansi(d.get('_percent_str', '0%')).replace('%', '')
                try:
                    percent = float(p_str)
                except ValueError:
                    pass
            
            speed = d.get('speed')
            speed_str = f"{format_size(speed)}/s" if speed else d.get('_speed_str', '')
            eta = d.get('eta')
            eta_str = f"{eta}s" if eta else d.get('_eta_str', '')
            
            download_tasks[task_id].update({
                "status": "downloading",
                "progress": percent,
                "speed": speed_str,
                "eta": eta_str,
                "downloaded_bytes": downloaded_bytes,
                "total_bytes": total_bytes,
                "downloaded_formatted": format_size(downloaded_bytes),
                "total_formatted": format_size(total_bytes) if total_bytes else "Calculating...",
                "step_message": f"Downloading: {percent}% ({speed_str})"
            })

        outtmpl = os.path.join(DOWNLOADS_DIR, f"{task_id}_%(title)s.%(ext)s")
        
        ydl_opts = get_base_ydl_opts(browser_cookie)
        ydl_opts.update({
            'outtmpl': outtmpl,
            'progress_hooks': [hook],
            'windowsfilenames': True,
            'overwrites': True,
            'nocheckcertificate': True,
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
                    f"bestvideo[height<={target_height}][vcodec^=avc]+bestaudio[ext=m4a]/"
                    f"bestvideo[height<={target_height}][ext=mp4]+bestaudio[ext=m4a]/"
                    f"bestvideo[height<={target_height}]+bestaudio/"
                    f"best[height<={target_height}]/best"
                )
            else:
                format_spec = "bestvideo[vcodec^=avc]+bestaudio[ext=m4a]/bestvideo[ext=mp4]+bestaudio[ext=m4a]/bestvideo+bestaudio/best"

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
            for fname in os.listdir(DOWNLOADS_DIR):
                if fname.startswith(task_id):
                    found_filepath = os.path.join(DOWNLOADS_DIR, fname)
                    break
        
        if found_filepath and os.path.exists(found_filepath):
            # If it's a video file, ensure NLE compatibility (H.264 + AAC + yuv420p for Premiere/After Effects)
            if option_type == 'video':
                found_filepath = ensure_nle_compatible(found_filepath, task_id)

            actual_filename = os.path.basename(found_filepath)
            clean_display_name = re.sub(rf'^{task_id}_', '', actual_filename)
            filesize = os.path.getsize(found_filepath)
            
            download_tasks[task_id].update({
                "status": "completed",
                "progress": 100.0,
                "filepath": found_filepath,
                "filename": clean_display_name,
                "filesize": filesize,
                "filesize_formatted": format_size(filesize),
                "step_message": "Ready to download!"
            })
        else:
            download_tasks[task_id].update({
                "status": "error",
                "error": "Could not locate completed output file."
            })

    except Exception as e:
        err_clean = strip_ansi(str(e))
        if "DOWNLOAD_STOPPED_BY_USER" in err_clean:
            download_tasks[task_id].update({
                "status": "stopped",
                "speed": "0 KB/s",
                "eta": "--",
                "step_message": "Download stopped by user."
            })
            # Clean up partial files
            try:
                for fname in os.listdir(DOWNLOADS_DIR):
                    if fname.startswith(task_id) and fname.endswith(('.part', '.ytdl')):
                        fpath = os.path.join(DOWNLOADS_DIR, fname)
                        if os.path.exists(fpath):
                            os.remove(fpath)
            except Exception:
                pass
        else:
            download_tasks[task_id].update({
                "status": "error",
                "error": err_clean,
                "step_message": f"Error: {err_clean[:60]}"
            })

def pause_download_task(task_id: str) -> bool:
    if task_id in download_tasks:
        pe = download_tasks[task_id].get("_pause_event")
        if pe:
            pe.clear()
            download_tasks[task_id]["status"] = "paused"
            download_tasks[task_id]["speed"] = "0 KB/s (Paused)"
            download_tasks[task_id]["step_message"] = "Download paused by user"
            return True
    return False

def resume_download_task(task_id: str) -> bool:
    if task_id in download_tasks:
        pe = download_tasks[task_id].get("_pause_event")
        if pe:
            pe.set()
            download_tasks[task_id]["status"] = "downloading"
            download_tasks[task_id]["step_message"] = "Resuming download..."
            return True
    return False

def stop_download_task(task_id: str) -> bool:
    if task_id in download_tasks:
        download_tasks[task_id]["_cancel_requested"] = True
        pe = download_tasks[task_id].get("_pause_event")
        if pe:
            pe.set()
        download_tasks[task_id]["status"] = "stopped"
        download_tasks[task_id]["step_message"] = "Stopping download..."
        return True
    return False

def create_download_task(url: str, option_id: str, option_type: str, browser_cookie: Optional[str] = None) -> str:
    task_id = str(uuid.uuid4())[:8]
    t = threading.Thread(
        target=start_download_thread,
        args=(task_id, url, option_id, option_type, browser_cookie),
        daemon=True
    )
    t.start()
    return task_id

def save_custom_cookies(cookie_content: str) -> bool:
    try:
        with open(COOKIES_FILE, "w", encoding="utf-8") as f:
            f.write(cookie_content)
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
    b_name = browser_name.lower().strip()
    try:
        cookie_jar = yt_dlp.cookies.extract_cookies_from_browser(b_name)
        cookie_count = len(cookie_jar) if cookie_jar else 0
        
        cookie_jar.save(filename=COOKIES_FILE, format="netscape", ignore_discard=True, ignore_expires=True)
        
        return {
            "success": True,
            "count": cookie_count,
            "message": f"Successfully imported {cookie_count} cookies from {browser_name.title()}!"
        }
    except Exception as e:
        err_msg = str(e)
        return {
            "success": False,
            "error": f"Failed to extract cookies from {browser_name.title()}: {err_msg}"
        }
