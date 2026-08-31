import os
import sys
import subprocess
import shutil
from PIL import Image

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

def build():
    print("=" * 60)
    print("  Building Standalone KRONOS 4K Desktop Executable (.exe)")
    print("=" * 60)
    
    os.chdir(BASE_DIR)
    
    # 1. Generate multi-size app.ico from KRONOS-Logo.png
    logo_path = os.path.join(BASE_DIR, "KRONOS-Logo.png")
    ico_path = os.path.join(BASE_DIR, "app.ico")
    if os.path.exists(logo_path):
        try:
            img = Image.open(logo_path)
            icon_sizes = [(16, 16), (24, 24), (32, 32), (48, 48), (64, 64), (128, 128), (256, 256)]
            img.save(ico_path, format="ICO", sizes=icon_sizes)
            # Also ensure logo is in ui/
            ui_logo = os.path.join(BASE_DIR, "ui", "logo.png")
            img.save(ui_logo, format="PNG")
            ui_ico = os.path.join(BASE_DIR, "ui", "favicon.ico")
            img.save(ui_ico, format="ICO", sizes=[(16, 16), (32, 32), (48, 48)])
            print("[+] Generated multi-resolution app.ico and UI logos from KRONOS-Logo.png")
        except Exception as e:
            print(f"[-] Warning: Failed to generate icon: {e}")

    # 2. Check for ffmpeg.exe
    ffmpeg_path = os.path.join(BASE_DIR, "ffmpeg.exe")
    if not os.path.exists(ffmpeg_path):
        system_ffmpeg = shutil.which("ffmpeg")
        if system_ffmpeg and os.path.exists(system_ffmpeg):
            shutil.copy2(system_ffmpeg, ffmpeg_path)
            print(f"[+] Found and copied system FFmpeg: {system_ffmpeg}")
        else:
            print("[-] Warning: ffmpeg.exe not found in desktop-app folder.")

    # 3. PyInstaller command arguments
    cmd = [
        sys.executable,
        "-m",
        "PyInstaller",
        "--noconfirm",
        "--clean",
        "--onefile",
        "--windowed",
        "--name", "Kronos4K",
        "--add-data", f"ui{os.pathsep}ui",
        "--add-data", f"pot_provider{os.pathsep}pot_provider",
        "--collect-all", "yt_dlp_plugins",
    ]
    
    if os.path.exists(ico_path):
        cmd.extend(["--icon", "app.ico"])
        cmd.extend(["--add-data", f"app.ico{os.pathsep}."])
        
    if os.path.exists(ffmpeg_path):
        cmd.extend(["--add-binary", f"ffmpeg.exe{os.pathsep}."])
        
    cmd.append("main.py")
    
    print("\n[+] Running PyInstaller...")
    print("Command:", " ".join(cmd))
    
    res = subprocess.run(cmd)
    
    if res.returncode == 0:
        dist_exe = os.path.join(BASE_DIR, "dist", "Kronos4K.exe")
        print("\n" + "=" * 60)
        print("  BUILD SUCCESSFUL!")
        print(f"  Executable created at: {dist_exe}")
        print("=" * 60)
    else:
        print("\n[-] Build failed with exit code:", res.returncode)

if __name__ == "__main__":
    build()
