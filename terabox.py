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
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/115.0.0.0 Safari/537.36",
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

        try:
            # Follow redirects to get the true URL (handling 1024tera, etc.)
            response = session.get(url, allow_redirects=True)
            final_url = response.url

            # Extract 'surl' (short url key)
            # URL patterns: terabox.com/s/1abcde or terabox.com/sharing/link?surl=abcde
            surl = ""
            params = parse_qs(urlparse(final_url).query)

            if 'surl' in params:
                surl = params['surl'][0]
            else:
                # Try path extraction
                path = urlparse(final_url).path
                if '/s/' in path:
                    surl = path.split('/s/')[-1]

            if not surl:
                return {"error": "Could not extract surl"}

            # If surl starts with '1', remove it for the API call usually?
            # Actually, the API parameter is 'shorturl'. If surl is '1-abc', shorturl is '1-abc'.

            # 2. Get File List via API
            # This is a known endpoint structure.
            api_url = "https://www.terabox.com/api/shorturlinfo"
            params = {
                "shorturl": surl,
                "root": "1",
            }

            # We need the 'jsToken' sometimes, but let's try with just cookies first.
            api_response = session.get(api_url, params=params)
            data = api_response.json()

            if data.get('errno') != 0:
                return {"error": f"API Error: {data.get('errno')}"}

            # Process file list
            file_list = []
            if 'list' in data:
                for item in data['list']:
                    file_list.append({
                        "fs_id": item.get('fs_id'),
                        "filename": item.get('server_filename'),
                        "size": int(item.get('size')),
                        "dlink": item.get('dlink'), # Note: dlink here might expire or need User-Agent
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
