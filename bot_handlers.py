from pyrogram import Client, filters
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton, Message, CallbackQuery
from config import Config
from database import db
import asyncio

# Initialize Client
app = Client(
    "terabox_bot",
    api_id=Config.API_ID,
    api_hash=Config.API_HASH,
    bot_token=Config.BOT_TOKEN
)

# --- Handlers ---

@app.on_message(filters.command("start") & filters.private)
async def start_handler(client: Client, message: Message):
    # Ensure user is in DB
    await db.add_user(message.from_user.id)

    buttons = InlineKeyboardMarkup([
        [InlineKeyboardButton("⬇️ Terabox Download", callback_data="download_mode")],
        [
            InlineKeyboardButton("📊 Stats", callback_data="stats"),
            InlineKeyboardButton("📞 Admin Contact", url="t.me/fr_sammm11")
        ]
    ])

    await message.reply_text(
        f"Hello {message.from_user.first_name}!\n\n"
        "I am a Terabox Downloader Bot.\n"
        "I can download videos, images, and files from Terabox links.\n\n"
        "Select an option below:",
        reply_markup=buttons
    )

@app.on_callback_query(filters.regex("download_mode"))
async def download_mode_cb(client: Client, callback: CallbackQuery):
    await callback.message.edit_text(
        "Send me any Terabox link to download.\n"
        "Supported types: Video, Image, File, Folder.\n\n"
        "Limit: 2GB per file (Split if > 2GB).",
        reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Back", callback_data="back_home")]])
    )

@app.on_callback_query(filters.regex("back_home"))
async def back_home_cb(client: Client, callback: CallbackQuery):
    await start_handler(client, callback.message)

if __name__ == "__main__":
    print("Bot is starting...")
    # app.run() # We will run this via main.py later
