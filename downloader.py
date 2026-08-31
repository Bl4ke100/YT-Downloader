import os
import re
import math
import uuid
import time
import threading
from typing import Dict, Any, Optional
import yt_dlp

DOWNLOADS_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "downloads")
os.makedirs(DOWNLOADS_DIR, exist_ok=True)

# In-memory store for download task progress
download_tasks: Dict[str, Dict[str, Any]] = {}

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
        return "Unknown size"
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

def extract_video_info(url: str) -> Dict[str, Any]:
    """
    Extracts video metadata, clean resolutions (up to 4K/8K), and audio options.
    """
    ydl_opts = {
        'skip_download': True,
        'quiet': True,
        'no_warnings': True,
        'extract_flat': False,
    }
    
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(url, download=False)
        
    duration = info.get('duration', 0)
    formats = info.get('formats', [])
    
    # Estimate audio size (best audio stream)
    best_audio_size = 0
    audio_formats = [f for f in formats if f.get('vcodec') == 'none' and f.get('acodec') != 'none']
    if audio_formats:
        best_audio = max(audio_formats, key=lambda f: f.get('abr', 0) or 0)
        best_audio_size = best_audio.get('filesize') or best_audio.get('filesize_approx') or 0
        if not best_audio_size and duration and best_audio.get('abr'):
            best_audio_size = int((best_audio.get('abr') * 1000 / 8) * duration)

    # Group video formats by standard resolution heights
    # Target heights: 4320 (8K), 2160 (4K), 1440 (2K), 1080 (FHD), 720 (HD), 480 (SD), 360 (SD)
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
        # Find video-only or muxed stream matching this height
        matching_v_formats = [
            f for f in formats 
            if f.get('height') and abs(f.get('height') - th) <= 10 and f.get('vcodec') != 'none'
        ]
        
        if matching_v_formats and th not in seen_heights:
            seen_heights.add(th)
            # Pick best format by bitrate or fps
            best_f = max(
                matching_v_formats, 
                key=lambda x: (x.get('fps') or 30, x.get('tbr') or x.get('vbr') or 0)
            )
            fps = best_f.get('fps')
            fps_str = f"{fps}fps" if fps and fps > 30 else ""
            
            # Calculate combined video + audio size
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
                "size_formatted": format_size(total_size) if total_size > 0 else "Estimated dynamically",
                "estimated_bytes": total_size
            })

    # If no standard matches found, extract unique heights available
    if not video_options:
        available_v = [f for f in formats if f.get('height') and f.get('vcodec') != 'none']
        sorted_v = sorted(available_v, key=lambda f: f.get('height', 0), reverse=True)
        unique_heights = {}
        for f in sorted_v:
            h = f.get('height')
            if h and h not in unique_heights:
                unique_heights[h] = f
        
        for h, f in unique_heights.items():
            video_options.append({
                "id": f"video_{h}",
                "type": "video",
                "height": h,
                "label": f"{h}p Video",
                "badge": f"{h}p",
                "fps": f"{f.get('fps')}fps" if f.get('fps', 0) > 30 else "",
                "tag": "HD" if h >= 720 else "SD",
                "ext": "mp4",
                "format_id": f.get('format_id'),
                "size_formatted": format_size(f.get('filesize') or f.get('filesize_approx')),
                "estimated_bytes": f.get('filesize') or 0
            })

    # Audio format options
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
            "label": "M4A / AAC (Original Audio Stream)",
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

    # Best thumbnail
    thumbnails = info.get('thumbnails', [])
    thumbnail_url = info.get('thumbnail')
    if thumbnails:
        # Sort by resolution/width if present
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

def sanitize_filename(name: str) -> str:
    return re.sub(r'[\\/*?:"<>|]', "", name).strip()

def start_download_thread(task_id: str, url: str, option_id: str, option_type: str, custom_format: Optional[str] = None):
    def hook(d):
        task = download_tasks.get(task_id)
        if not task:
            return
        
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
                "step_message": f"Downloading stream: {percent}% ({speed_str})"
            })
            
        elif status == 'finished':
            task.update({
                "status": "processing",
                "progress": 99.0,
                "step_message": "Merging video & audio streams with FFmpeg..."
            })

    try:
        download_tasks[task_id] = {
            "task_id": task_id,
            "status": "starting",
            "progress": 0,
            "speed": "0 KB/s",
            "eta": "--",
            "step_message": "Initializing download streams...",
            "filename": None,
            "filepath": None,
            "filesize": 0,
            "error": None,
            "created_at": time.time()
        }

        out_template = os.path.join(DOWNLOADS_DIR, f"{task_id}_%(title).100s.%(ext)s")

        ydl_opts: Dict[str, Any] = {
            'outtmpl': out_template,
            'progress_hooks': [hook],
            'quiet': True,
            'no_warnings': True,
        }

        if option_type == 'audio':
            # Audio download & extraction
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
            # Video download with quality selection up to 4k / 8k
            m = re.search(r'video_(\d+)', option_id)
            target_height = int(m.group(1)) if m else None
            
            if target_height:
                # Format string: best video stream matching target_height (e.g., 2160p for 4k) + best audio stream
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

        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            res = ydl.extract_info(url, download=True)
            
            # Find the actual written file
            found_filepath = None
            if 'requested_downloads' in res and res['requested_downloads']:
                found_filepath = res['requested_downloads'][0].get('filepath')
            
            if not found_filepath or not os.path.exists(found_filepath):
                # Scan DOWNLOADS_DIR for prefix task_id
                for fname in os.listdir(DOWNLOADS_DIR):
                    if fname.startswith(task_id):
                        found_filepath = os.path.join(DOWNLOADS_DIR, fname)
                        break
            
            if found_filepath and os.path.exists(found_filepath):
                actual_filename = os.path.basename(found_filepath)
                # Strip internal task ID from user download filename
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
        download_tasks[task_id].update({
            "status": "error",
            "error": str(e),
            "step_message": f"Error: {str(e)}"
        })

def create_download_task(url: str, option_id: str, option_type: str) -> str:
    task_id = str(uuid.uuid4())[:8]
    thread = threading.Thread(
        target=start_download_thread,
        args=(task_id, url, option_id, option_type),
        daemon=True
    )
    thread.start()
    return task_id
