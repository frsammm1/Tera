import os
import time
import math
import aiohttp
import asyncio

class Downloader:
    def __init__(self):
        pass

    async def download_file(self, url, filename, headers=None, cookies=None, progress_callback=None):
        async with aiohttp.ClientSession(cookies=cookies) as session:
            # Use provided headers or fallback
            if not headers:
                headers = {
                    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/115.0.0.0 Safari/537.36",
                     "Referer": "https://www.terabox.com/"
                }

            try:
                async with session.get(url, headers=headers) as response:
                    if response.status != 200:
                        return None, f"HTTP Error {response.status}"

                    total_size = int(response.headers.get("Content-Length", 0))
                    downloaded = 0
                    start_time = time.time()
                    last_update_time = 0

                    with open(filename, "wb") as f:
                        async for chunk in response.content.iter_chunked(1024 * 1024): # 1MB chunks
                            if chunk:
                                f.write(chunk)
                                downloaded += len(chunk)

                                # Update progress every 7-8 seconds
                                current_time = time.time()
                                if progress_callback and (current_time - last_update_time > 7):
                                    await progress_callback(downloaded, total_size, "Downloading")
                                    last_update_time = current_time

                    return filename, None
            except Exception as e:
                return None, str(e)

# Helper for progress display
def humanbytes(size):
    if not size:
        return ""
    power = 2**10
    n = 0
    Dic_powerN = {0: ' ', 1: 'Ki', 2: 'Mi', 3: 'Gi', 4: 'Ti'}
    while size > power:
        size /= power
        n += 1
    return str(round(size, 2)) + " " + Dic_powerN[n] + 'B'

async def progress_bar(current, total, status_text, message, start_time):
    # This will be called by the bot handler, updating the message
    # Logic:
    # [■■■■■■□□□□] 60%
    # 300MB / 500MB
    # Speed: 5MB/s
    # ETA: 40s

    now = time.time()
    diff = now - start_time
    if diff == 0:
        diff = 1
    speed = current / diff
    percentage = current * 100 / total
    speed_text = f"{humanbytes(speed)}/s"
    eta = (total - current) / speed
    eta_text = f"{round(eta)}s"

    # Progress bar
    completed = int(percentage // 10)
    bar = "■" * completed + "□" * (10 - completed)

    text = f"{status_text}\n" \
           f"[{bar}] {round(percentage, 2)}%\n" \
           f"{humanbytes(current)} / {humanbytes(total)}\n" \
           f"Speed: {speed_text} | ETA: {eta_text}"

    try:
        await message.edit_text(text)
    except Exception:
        pass
