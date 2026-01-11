import time
import os
from pyrogram import Client
from config import Config
from downloader import progress_bar

class Uploader:
    def __init__(self):
        pass

    async def upload_file(self, client: Client, file_path, chat_id, message, log_channel_id=None):
        # Determine file type
        ext = os.path.splitext(file_path)[1].lower()

        start_time = time.time()
        last_update_time = 0

        async def _progress(current, total):
            nonlocal last_update_time
            now = time.time()
            if now - last_update_time > 7:
                await progress_bar(current, total, "Uploading", message, start_time)
                last_update_time = now

        try:
            sent_msg = None
            if ext in ['.mp4', '.mkv', '.avi', '.mov']:
                # Video (get thumb/duration/width/height ideally, but basic for now)
                sent_msg = await client.send_video(
                    chat_id=chat_id,
                    video=file_path,
                    caption=os.path.basename(file_path),
                    progress=_progress,
                    supports_streaming=True
                )
            elif ext in ['.jpg', '.jpeg', '.png', '.webp']:
                sent_msg = await client.send_photo(
                    chat_id=chat_id,
                    photo=file_path,
                    caption=os.path.basename(file_path),
                    progress=_progress
                )
            elif ext in ['.mp3', '.flac', '.wav']:
                sent_msg = await client.send_audio(
                    chat_id=chat_id,
                    audio=file_path,
                    caption=os.path.basename(file_path),
                    progress=_progress
                )
            else:
                sent_msg = await client.send_document(
                    chat_id=chat_id,
                    document=file_path,
                    caption=os.path.basename(file_path),
                    progress=_progress
                )

            # Forward to Log Channel
            if log_channel_id and sent_msg:
                # We can copy the message to avoid re-uploading
                await sent_msg.copy(log_channel_id)

            return True

        except Exception as e:
            await message.edit_text(f"Upload Error: {e}")
            return False

uploader = Uploader()
