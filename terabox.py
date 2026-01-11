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
            return {"error": "Empty URL"}

        session = requests.Session()
        session.cookies.update(self.get_cookies_dict())
        session.headers.update(self.get_headers())

        surl = ""

        try:
            # Attempt 1: Follow redirects
            try:
                # Some shortlinks like teraboxshare.com require handling
                # We do not verify SSL for obscure shorteners if needed, but Terabox should be fine.
                response = session.get(url, allow_redirects=True, timeout=15)
                final_url = response.url

                # Check if we landed on an error page or similar
                if "error" in final_url or response.status_code >= 400:
                    print(f"Warning: Redirect ended at {final_url} with status {response.status_code}")
                    # Don't raise immediately, try parsing original url if redirect failed

                # Extract SURL from final URL
                surl = self._extract_surl(final_url)

            except Exception as e:
                print(f"Redirect Error: {e}")

            # If redirect didn't give surl, try original URL
            if not surl:
                surl = self._extract_surl(url)

            if not surl:
                return {"error": "Could not extract surl from link. Please make sure it is a valid Terabox/1024tera link."}

            # Prepend '1' if missing, but be careful (sometimes it's not needed, but usually is for API)
            # Most 1024tera links extract as 'q_...' and need '1q_...' for the API.
            if not surl.startswith("1"):
                surl = "1" + surl

            print(f"Processing surl: {surl}")

            # 2. Get File List via API
            # Note: We use www.terabox.com even if the link was 1024tera, as the API is centralized.
            api_url = "https://www.terabox.com/api/shorturlinfo"
            params = {
                "shorturl": surl,
                "root": "1",
            }

            api_response = session.get(api_url, params=params)
            data = api_response.json()

            if data.get('errno') != 0:
                errno = data.get('errno')
                error_msg = f"API Error {errno}: {data.get('errmsg', 'Unknown')}"
                if errno == 105:
                    error_msg = "Link is expired or deleted (Error 105)"
                elif errno == 2:
                    error_msg = "Login Expired. Please update cookies (Error 2)"
                elif errno == 4000020:
                     error_msg = "Invalid Short URL or Permission Denied (Error 4000020)"
                return {"error": error_msg}

            # Process file list
            files = []
            if 'list' in data:
                for item in data['list']:
                    if item.get('isdir') == "1":
                        # Fetch folder content
                        print(f"Found folder: {item.get('path')}")
                        folder_files = self.fetch_folder(session, surl, item.get('path'))
                        files.extend(folder_files)
                    else:
                        files.append(self.parse_item(item))

            if not files:
                 return {"error": "No files found. The link might be empty or valid cookies are required to view content."}

            return {
                "files": files,
                "shareid": data.get('shareid'),
                "uk": data.get('uk'),
            }

        except Exception as e:
            import traceback
            traceback.print_exc()
            return {"error": str(e)}

    def _extract_surl(self, url):
        surl = None
        try:
            parsed = urlparse(url)

            # Method A: Path /s/1xxx
            path_parts = parsed.path.split('/')
            if 's' in path_parts:
                idx = path_parts.index('s')
                if idx + 1 < len(path_parts):
                    candidate = path_parts[idx+1]
                    if candidate:
                        surl = candidate

            # Method B: Query param surl=1xxx
            if not surl:
                qs = parse_qs(parsed.query)
                if 'surl' in qs:
                    surl = qs['surl'][0]

            # Method C: Handle sharing/link?surl=...
            if not surl and 'sharing/link' in parsed.path:
                 qs = parse_qs(parsed.query)
                 if 'surl' in qs:
                    surl = qs['surl'][0]

        except Exception as e:
            print(f"Error extracting SURL: {e}")

        return surl

    def fetch_folder(self, session, surl, dir_path):
        url = "https://www.terabox.com/share/list"
        params = {
            "shorturl": surl,
            "dir": dir_path,
            "root": "0"
        }

        files = []
        try:
            res = session.get(url, params=params)
            data = res.json()

            if data.get('errno') == 0 and 'list' in data:
                for item in data['list']:
                    if item.get('isdir') == "1":
                         # Recursive fetch
                         files.extend(self.fetch_folder(session, surl, item.get('path')))
                    else:
                        files.append(self.parse_item(item))
        except Exception as e:
            print(f"Error fetching folder {dir_path}: {e}")

        return files

    def parse_item(self, item):
        fs_id = item.get('fs_id')
        filename = item.get('server_filename')
        if not filename:
            filename = f"terabox_file_{fs_id}"

        return {
            "fs_id": fs_id,
            "filename": filename,
            "size": int(item.get('size', 0)),
            "dlink": item.get('dlink'), # Might be empty if not logged in
            "is_dir": False
        }

terabox = TeraboxClient()
