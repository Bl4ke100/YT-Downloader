import os
import sys
import time
import threading
from http.cookies import SimpleCookie
import webview
import downloader

def cookies_to_netscape(cookie_list):
    lines = [
        "# Netscape HTTP Cookie File",
        "# Exported from KRONOS In-App YouTube Sign-In",
        ""
    ]
    seen = set()
    for sc in cookie_list:
        try:
            if isinstance(sc, SimpleCookie):
                for name, morsel in sc.items():
                    domain = morsel['domain'] or '.youtube.com'
                    if not domain.startswith('.'):
                        domain = '.' + domain
                    flag = "TRUE" if str(domain).startswith('.') else "FALSE"
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
    return all_cookies

def main():
    login_win = webview.create_window(
        title="KRONOS - Sign In to YouTube (Auto-closes when signed in)",
        url="https://accounts.google.com/ServiceLogin?service=youtube&continue=https://www.youtube.com/",
        width=560,
        height=720,
        resizable=True
    )

    def auto_save_and_close_watcher():
        for _ in range(180): # 3 mins max
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

                has_auth_key = any(k in ['LOGIN_INFO', 'SID', 'SSID', 'HSID', 'SAPISID', 'APISID'] for k in cookie_names)
                is_on_yt = 'youtube.com' in current_url and 'accounts.google.com' not in current_url

                if has_auth_key and is_on_yt:
                    time.sleep(2)
                    final_cookies = extract_all_cookies(login_win)
                    netscape_txt = cookies_to_netscape(final_cookies)
                    downloader.save_custom_cookies(netscape_txt)
                    try:
                        login_win.destroy()
                    except Exception:
                        pass
                    break
            except Exception:
                break

    threading.Thread(target=auto_save_and_close_watcher, daemon=True).start()
    
    def on_closed():
        try:
            cookies = extract_all_cookies(login_win)
            if cookies:
                netscape_txt = cookies_to_netscape(cookies)
                if len(cookies) > 0:
                    downloader.save_custom_cookies(netscape_txt)
        except Exception:
            pass

    try:
        login_win.events.closed += on_closed
    except Exception:
        pass

    webview.start()

if __name__ == "__main__":
    main()
