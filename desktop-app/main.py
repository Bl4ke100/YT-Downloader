import os
import sys
import time
import threading
import ctypes
from ctypes import wintypes
from http.cookies import SimpleCookie
import subprocess
import webview
import downloader_core
import engine_updater
engine_updater.ensure_engine_path()

def cookies_to_netscape(cookies_list) -> str:
    lines = [
        "# Netscape HTTP Cookie File",
        "# Generated automatically by KRONOS 4K In-App Login",
        ""
    ]
    seen = set()
    for sc in cookies_list:
        try:
            if isinstance(sc, SimpleCookie):
                for name, morsel in sc.items():
                    domain = morsel['domain'] or '.youtube.com'
                    if not domain.startswith('.'):
                        domain = '.' + domain
                    flag = "TRUE" if domain.startswith('.') else "FALSE"
                    path = morsel['path'] or '/'
                    secure = "TRUE" if morsel['secure'] else "FALSE"
                    exp_ts = str(int(time.time() + 86400 * 365))
                    val = morsel.value
                    key = (domain, path, name)
                    if key not in seen and name and val:
                        seen.add(key)
                        lines.append(f"{domain}\t{flag}\t{path}\t{secure}\t{exp_ts}\t{name}\t{val}")
            else:
                name = getattr(sc, 'name', '') or getattr(sc, 'Name', '') or getattr(sc, 'key', '')
                val = getattr(sc, 'value', '') or getattr(sc, 'Value', '')
                domain = getattr(sc, 'domain', '') or getattr(sc, 'Domain', '') or '.youtube.com'
                if not domain.startswith('.'):
                    domain = '.' + domain
                flag = "TRUE" if str(domain).startswith('.') else "FALSE"
                path = getattr(sc, 'path', '/') or getattr(sc, 'Path', '/') or '/'
                secure = "TRUE" if getattr(sc, 'secure', False) or getattr(sc, 'Secure', False) else "FALSE"
                exp_ts = str(int(time.time() + 86400 * 365))
                key = (domain, path, name)
                if key not in seen and name and val:
                    seen.add(key)
                    lines.append(f"{domain}\t{flag}\t{path}\t{secure}\t{exp_ts}\t{name}\t{val}")
        except Exception:
            continue
    return "\n".join(lines)

def extract_all_cookies(login_win):
    all_cookies = []
    try:
        c = login_win.get_cookies()
        if c:
            all_cookies.extend(c)
    except Exception:
        pass
        
    try:
        form = login_win.native
        browser = getattr(form, 'browser', None)
        if browser:
            for u in ['https://www.youtube.com', 'https://youtube.com', 'https://accounts.google.com', 'https://google.com']:
                try:
                    browser.url = u
                    c = login_win.get_cookies()
                    if c:
                        all_cookies.extend(c)
                except Exception:
                    pass
    except Exception:
        pass
    return all_cookies

class DesktopApi:
    def __init__(self):
        self._window = None
        self._login_window = None

    def set_window(self, window):
        self._window = window

    # Native Folder Selection
    def select_download_folder(self):
        if not self._window:
            return downloader_core.get_default_downloads_dir()
        result = self._window.create_file_dialog(webview.FOLDER_DIALOG)
        if result and len(result) > 0:
            return result[0]
        return None

    def get_default_downloads_dir(self):
        return downloader_core.get_default_downloads_dir()

    # Core Downloader Bridge
    def fetch_video_info(self, url, browser_cookie=None):
        try:
            return {
                "success": True,
                "data": downloader_core.extract_video_info(url, browser_cookie)
            }
        except Exception as e:
            return {
                "success": False,
                "error": downloader_core.strip_ansi(str(e))
            }

    def start_download_task(self, url, option_id, option_type, save_dir=None, browser_cookie=None):
        try:
            target_dir = save_dir or downloader_core.get_default_downloads_dir()
            task_id = downloader_core.create_download_task(
                url=url,
                option_id=option_id,
                option_type=option_type,
                save_dir=target_dir,
                browser_cookie=browser_cookie
            )
            return {"success": True, "task_id": task_id}
        except Exception as e:
            return {"success": False, "error": downloader_core.strip_ansi(str(e))}

    def get_download_progress(self, task_id):
        task = downloader_core.active_tasks.get(task_id)
        if not task:
            return {"status": "not_found"}
        return {k: v for k, v in task.items() if not k.startswith("_")}

    def reveal_in_explorer(self, filepath):
        try:
            if filepath and os.path.exists(filepath):
                norm_path = os.path.normpath(filepath)
                subprocess.run(f'explorer /select,"{norm_path}"', shell=True)
                return {"success": True}
            else:
                downloads_dir = downloader_core.get_default_downloads_dir()
                subprocess.run(f'explorer /select,"{downloads_dir}"', shell=True)
                return {"success": True}
        except Exception as e:
            return {"success": False, "error": str(e)}

    # Download Lifecycle Controls
    def pause_download(self, task_id):
        ok = downloader_core.pause_download_task(task_id)
        return {"success": ok}

    def resume_download(self, task_id):
        ok = downloader_core.resume_download_task(task_id)
        return {"success": ok}

    def stop_download(self, task_id):
        ok = downloader_core.stop_download_task(task_id)
        return {"success": ok}

    # Cookie Authentication
    def check_cookies(self):
        return {"has_cookies": downloader_core.has_cookies_file()}

    def save_cookies(self, content):
        ok = downloader_core.save_custom_cookies(content)
        return {"success": ok}

    def clear_cookies(self):
        ok = downloader_core.clear_custom_cookies()
        return {"success": ok}

    def import_browser_cookies(self, browser_name):
        try:
            return downloader_core.import_cookies_from_browser(browser_name)
        except Exception as e:
            return {"success": False, "error": str(e)}

    # Engine Updates (yt-dlp)
    def check_engine_update(self):
        return engine_updater.check_engine_update()

    def install_engine_update(self):
        return engine_updater.install_engine_update()

    def open_external_url(self, url):
        try:
            import webbrowser
            webbrowser.open(url)
            return {"success": True}
        except Exception as e:
            return {"success": False, "error": str(e)}

    # 1-Click In-App YouTube Login with Multi-Domain Cookie Capture
    def launch_youtube_login(self):
        try:
            login_win = webview.create_window(
                title="KRONOS - Sign In to YouTube (Auto-closes when signed in)",
                url="https://accounts.google.com/ServiceLogin?service=youtube&continue=https://www.youtube.com/",
                width=560,
                height=720,
                resizable=True
            )
            self._login_window = login_win

            def auto_save_and_close_watcher():
                # Poll for Google/YouTube session cookies and redirect
                for _ in range(180): # Wait up to 3 minutes
                    time.sleep(1.5)
                    try:
                        current_url = ""
                        try:
                            current_url = login_win.get_current_url() or ""
                        except Exception:
                            pass

                        cookies = extract_all_cookies(login_win)
                        if not cookies:
                            continue
                        
                        cookie_names = []
                        for sc in cookies:
                            if isinstance(sc, SimpleCookie):
                                cookie_names.extend(list(sc.keys()))
                            else:
                                n = getattr(sc, 'name', '') or getattr(sc, 'Name', '') or getattr(sc, 'key', '')
                                if n:
                                    cookie_names.append(n)
                        
                        # Check for critical auth tokens
                        has_auth_key = any(k in ['LOGIN_INFO', 'SID', 'SSID', 'HSID', 'SAPISID', 'APISID'] for k in cookie_names)
                        is_on_yt = 'youtube.com' in current_url and 'accounts.google.com' not in current_url

                        if has_auth_key and is_on_yt:
                            time.sleep(2) # Let all final auth cookies settle
                            final_cookies = extract_all_cookies(login_win)
                            netscape_txt = cookies_to_netscape(final_cookies)
                            downloader_core.save_custom_cookies(netscape_txt)
                            
                            try:
                                login_win.destroy()
                            except Exception:
                                pass
                            break
                    except Exception:
                        break

            threading.Thread(target=auto_save_and_close_watcher, daemon=True).start()

            def on_manual_closed():
                try:
                    cookies = extract_all_cookies(login_win)
                    if cookies:
                        netscape_txt = cookies_to_netscape(cookies)
                        if len(cookies) > 0:
                            downloader_core.save_custom_cookies(netscape_txt)
                except Exception:
                    pass

            login_win.events.closed += on_manual_closed
            return {"success": True}
        except Exception as e:
            return {"success": False, "error": str(e)}

def get_asset_path(filename):
    if getattr(sys, 'frozen', False):
        base = sys._MEIPASS
    else:
        base = os.path.dirname(os.path.abspath(__file__))
    return os.path.join(base, "ui", filename)

def get_root_asset(filename):
    if getattr(sys, 'frozen', False):
        base = sys._MEIPASS
    else:
        base = os.path.dirname(os.path.abspath(__file__))
    return os.path.join(base, filename)

def setup_windows_theme(window_title="KRONOS 4K - YouTube Downloader"):
    """Applies deep black immersive dark titlebar and window icon on Windows."""
    if sys.platform != "win32":
        return

    time.sleep(0.3)
    user32 = ctypes.windll.user32
    dwmapi = ctypes.windll.dwmapi
    
    hwnd = 0
    for _ in range(20):
        hwnd = user32.FindWindowW(None, window_title)
        if hwnd:
            break
        time.sleep(0.1)
        
    if not hwnd:
        return

    # 1. DWM Immersive Dark Mode
    DWMWA_USE_IMMERSIVE_DARK_MODE = 20
    DWMWA_USE_IMMERSIVE_DARK_MODE_OLD = 19
    DWMWA_CAPTION_COLOR = 35
    DWMWA_TEXT_COLOR = 36
    
    dark_val = ctypes.c_int(1)
    res = dwmapi.DwmSetWindowAttribute(
        hwnd, DWMWA_USE_IMMERSIVE_DARK_MODE, ctypes.byref(dark_val), ctypes.sizeof(dark_val)
    )
    if res != 0:
        dwmapi.DwmSetWindowAttribute(
            hwnd, DWMWA_USE_IMMERSIVE_DARK_MODE_OLD, ctypes.byref(dark_val), ctypes.sizeof(dark_val)
        )

    # 2. Match background color #08080a (BGR: 0x000A0808) & white caption text
    caption_color = ctypes.c_int(0x000A0808)
    dwmapi.DwmSetWindowAttribute(
        hwnd, DWMWA_CAPTION_COLOR, ctypes.byref(caption_color), ctypes.sizeof(caption_color)
    )
    text_color = ctypes.c_int(0x00FFFFFF)
    dwmapi.DwmSetWindowAttribute(
        hwnd, DWMWA_TEXT_COLOR, ctypes.byref(text_color), ctypes.sizeof(text_color)
    )

    # 3. Load & set native Window Titlebar Icon
    ico_path = get_root_asset("app.ico")
    if os.path.exists(ico_path):
        IMAGE_ICON = 1
        LR_LOADFROMFILE = 0x00000010
        LR_DEFAULTSIZE = 0x00000040
        WM_SETICON = 0x0080
        ICON_SMALL = 0
        ICON_BIG = 1

        h_icon = user32.LoadImageW(
            None, ico_path, IMAGE_ICON, 32, 32, LR_LOADFROMFILE
        )
        h_icon_sm = user32.LoadImageW(
            None, ico_path, IMAGE_ICON, 16, 16, LR_LOADFROMFILE
        )
        if h_icon:
            user32.SendMessageW(hwnd, WM_SETICON, ICON_BIG, h_icon)
        if h_icon_sm:
            user32.SendMessageW(hwnd, WM_SETICON, ICON_SMALL, h_icon_sm)

_pot_process = None

def _pot_worker():
    global _pot_process
    import urllib.request
    try:
        with urllib.request.urlopen('http://127.0.0.1:4416/ping', timeout=0.5) as resp:
            if resp.status == 200:
                return
    except Exception:
        pass
    
    server_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "pot_provider", "server")
    main_js = os.path.join(server_dir, "build", "main.js")
    if os.path.exists(main_js):
        try:
            _pot_process = subprocess.Popen(
                ["node", main_js, "--port", "4416"],
                cwd=server_dir,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                creationflags=subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0
            )
        except Exception:
            pass

def ensure_pot_server_async():
    """Starts the local Botguard PO-Token provider in the background without blocking window launch."""
    t = threading.Thread(target=_pot_worker, daemon=True)
    t.start()

def main():
    ensure_pot_server_async()
    api = DesktopApi()
    html_path = get_asset_path("index.html")

    window_title = "KRONOS 4K - YouTube Downloader"
    window = webview.create_window(
        title=window_title,
        url=html_path,
        js_api=api,
        width=1040,
        height=780,
        min_size=(780, 560),
        resizable=True,
        frameless=False,
        background_color="#08080a"
    )
    api.set_window(window)

    def on_start():
        setup_windows_theme(window_title)

    try:
        webview.start(on_start, debug=False)
    finally:
        global _pot_process
        if _pot_process:
            try:
                _pot_process.terminate()
            except Exception:
                pass

if __name__ == "__main__":
    main()

