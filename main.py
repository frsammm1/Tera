import asyncio
import os
import time
from pyrogram import Client, filters, idle
from pyrogram.types import Message, CallbackQuery
from config import Config
from database import db
from terabox import terabox
from downloader import Downloader, progress_bar
from splitter import splitter
from uploader import uploader
# Import handlers to register them
import bot_handlers
import admin_handlers

# Initialize Client (reuse from bot_handlers or create new instance logic)
# Since we defined 'app' in bot_handlers, we should import it.
from bot_handlers import app, ACTIVE_DOWNLOADS

# --- Main Logic for Links ---

# State storage (simple in-memory for now)
user_states = {} # {user_id: "state"}

@app.on_message(filters.text & filters.private)
async def text_handler(client: Client, message: Message):
    user_id = message.from_user.id
    text = message.text

    # Check if command (already handled by other handlers)
    if text.startswith("/"):
        return

    # Check Access
    allowed, status = await db.check_access(user_id)
    if not allowed:
        if status == "BANNED":
            await message.reply_text("🚫 You are banned from using this bot.")
        elif status == "EXPIRED":
            await message.reply_text("⏳ Your subscription/credits have expired.\nContact Admin to renew: t.me/fr_sammm11\nUse /buy to request.")
        return

    # Check for Terabox Link
    if "terabox" in text or "1024tera" in text:
        # Process Link
        status_msg = await message.reply_text("🔎 Processing Terabox Link...")

        # Add to active downloads
        ACTIVE_DOWNLOADS.add(user_id)

        try:
            # 1. Get Data
            data = terabox.get_data(text)

            if not data or "error" in data:
                await status_msg.edit_text(f"❌ Error extracting link: {data.get('error') if data else 'Unknown'}")
                return

            files = data.get("files", [])
            if not files:
                 await status_msg.edit_text("❌ No files found in link.")
                 return

            await status_msg.edit_text(f"✅ Found {len(files)} files. Starting download...")

            # Reduce credit if FREE
            if status == "FREE":
                if not await db.reduce_credit(user_id):
                    await status_msg.edit_text("⚠️ Credits finished just now.")
                    return

            downloader = Downloader()
            cookies = terabox.get_cookies_dict()

            for file_info in files:
                dlink = file_info.get('dlink')
                filename = file_info.get('filename')
                size = file_info.get('size')

                # Check 2GB Limit for download safety if disk is small,
                # but we are splitting so it's okay IF we have disk space.

                # Download
                await status_msg.edit_text(f"⬇️ Downloading: {filename}")
                local_path, error = await downloader.download_file(
                    dlink,
                    filename,
                    cookies=cookies,
                    progress_callback=lambda c, t, s: progress_bar(c, t, s, status_msg, time.time())
                )

                if error:
                    await status_msg.edit_text(f"❌ Download Failed: {error}")
                    continue

                # Split if needed
                paths_to_upload = [local_path]
                if size > 2 * 1024 * 1024 * 1024: # > 2GB
                    await status_msg.edit_text("✂️ File > 2GB. Splitting...")
                    paths_to_upload = splitter.split_file(local_path)
                    # Remove original large file to save space
                    if len(paths_to_upload) > 1 and os.path.exists(local_path):
                        os.remove(local_path)

                # Upload
                for path in paths_to_upload:
                    await status_msg.edit_text(f"⬆️ Uploading: {os.path.basename(path)}")
                    success = await uploader.upload_file(
                        client,
                        path,
                        user_id,
                        status_msg,
                        log_channel_id=Config.LOG_CHANNEL_ID
                    )

                    # Clean up uploaded part
                    if os.path.exists(path):
                        os.remove(path)

                await status_msg.edit_text(f"✅ Completed: {filename}")

        except Exception as e:
            await status_msg.edit_text(f"⚠️ Error: {e}")
        finally:
            if user_id in ACTIVE_DOWNLOADS:
                ACTIVE_DOWNLOADS.remove(user_id)

    else:
        # Not a link, maybe chat?
        # Only reply if user was asked for a link (State machine could be used here)
        await message.reply_text("Please send a valid Terabox link.")


if __name__ == "__main__":
    print("Starting Bot...")
    app.run()
