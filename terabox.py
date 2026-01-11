import os
import requests
import http.cookiejar
from urllib.parse import urlparse, parse_qs
import json
import re

class TeraboxClient:
    def __init__(self, cookie_file='www.terabox.com_cookies.txt'):
        self.cookie_file = cookie_file
        self.cj = http.cookiejar.MozillaCookieJar(self.cookie_file)
        try:
            self.cj.load()
        except Exception as e:
            print(f"Error loading cookies: {e}")
            self.cj = None

    def get_cookies_dict(self):
        cookies = {}
        if self.cj:
            for cookie in self.cj:
                cookies[cookie.name] = cookie.value
        return cookies

    def get_headers(self):
        return {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.5",
            "Connection": "keep-alive",
            "Referer": "https://www.terabox.com/"
        }

    def get_data(self, url):
        # 1. Normalize URL
        if not url:
            return None

        session = requests.Session()
        session.cookies.update(self.get_cookies_dict())
        session.headers.update(self.get_headers())

        surl = ""

        try:
            # Attempt 1: Follow redirects
            try:
                response = session.get(url, allow_redirects=True, timeout=10)
                final_url = response.url

                # Check if we landed on an error page or similar
                if "error" in final_url or response.status_code == 404:
                    raise Exception("Redirected to error page")

                params = parse_qs(urlparse(final_url).query)
                if 'surl' in params:
                    surl = params['surl'][0]
                else:
                    path = urlparse(final_url).path
                    if '/s/' in path:
                        surl = path.split('/s/')[-1]
            except Exception as e:
                # Fallback: Extract from initial URL string if requests failed
                # This handles cases where the domain is blocked or redirects to 404
                # pattern: /s/1abcde
                print(f"Extraction fallback due to: {e}")
                path = urlparse(url).path
                if '/s/' in path:
                    surl = path.split('/s/')[-1]
                else:
                     # Attempt to find surl param in query
                    params = parse_qs(urlparse(url).query)
                    if 'surl' in params:
                        surl = params['surl'][0]

            if not surl:
                return {"error": "Could not extract surl"}

            # FIX: API requires shorturl to start with '1'
            if not surl.startswith("1"):
                surl = "1" + surl

            # 2. Get File List via API
            api_url = "https://www.terabox.com/api/shorturlinfo"
            params = {
                "shorturl": surl,
                "root": "1",
            }

            api_response = session.get(api_url, params=params)
            data = api_response.json()

            if data.get('errno') != 0:
                errno = data.get('errno')
                error_msg = f"API Error: {errno}"
                if errno == 105:
                    error_msg = "Link is expired or deleted (Error 105)"
                elif errno == 2:
                    error_msg = "Invalid Link or Cookies Expired (Error 2)"
                return {"error": error_msg}

            # Process file list
            file_list = []
            if 'list' in data:
                for item in data['list']:
                    fs_id = item.get('fs_id')
                    filename = item.get('server_filename') or f"terabox_file_{fs_id}"
                    file_list.append({
                        "fs_id": fs_id,
                        "filename": filename,
                        "size": int(item.get('size')),
                        "dlink": item.get('dlink'),
                        "is_dir": item.get('isdir') == "1"
                    })

            return {
                "files": file_list,
                "shareid": data.get('shareid'),
                "uk": data.get('uk'),
                "sign": data.get('sign'),
                "timestamp": data.get('timestamp')
            }

        except Exception as e:
            return {"error": str(e)}

terabox = TeraboxClient()
