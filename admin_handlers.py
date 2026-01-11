import time
import psutil
import shutil
import os
from pyrogram import Client, filters
from pyrogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from config import Config
from database import db
from bot_handlers import app

# Admin Helpers
async def is_admin(user_id):
    return user_id == Config.ADMIN_ID

# --- Admin Commands ---

@app.on_message(filters.command("add_user") & filters.private)
async def add_user_cmd(client: Client, message: Message):
    if not await is_admin(message.from_user.id):
        return

    # Syntax: /add_user <id> <duration><unit>
    try:
        args = message.command
        if len(args) != 3:
            await message.reply_text("Usage: `/add_user <user_id> <time><m/h/d>`\nExample: `/add_user 123456 30d`")
            return

        target_id = int(args[1])
        duration_str = args[2].lower()

        unit = duration_str[-1]
        value = int(duration_str[:-1])

        seconds = 0
        if unit == 'm':
            seconds = value * 60
        elif unit == 'h':
            seconds = value * 3600
        elif unit == 'd':
            seconds = value * 86400
        else:
            await message.reply_text("Invalid unit. Use m, h, or d.")
            return

        new_expiry = await db.update_expiry(target_id, seconds)
        await db.unban_user(target_id) # Unban if they were banned

        # Calculate expiry date string
        expiry_str = time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(new_expiry))
        await message.reply_text(f"User {target_id} added/extended until {expiry_str}.")

    except ValueError:
        await message.reply_text("Invalid ID or Value.")
    except Exception as e:
        await message.reply_text(f"Error: {e}")

@app.on_message(filters.command("revoke") & filters.private)
async def revoke_cmd(client: Client, message: Message):
    if not await is_admin(message.from_user.id):
        return

    try:
        args = message.command
        if len(args) != 2:
            await message.reply_text("Usage: `/revoke <user_id>`")
            return

        target_id = int(args[1])
        await db.revoke_access(target_id)
        await message.reply_text(f"User {target_id} access revoked.")

    except ValueError:
        await message.reply_text("Invalid ID.")

@app.on_callback_query(filters.regex("stats"))
async def stats_cb(client: Client, callback: CallbackQuery):
    # Check if admin (optional, but requested as 'Admin Panel')
    # User requirement: "Admin contact... stats (active downloads)" on start.
    # Also "Admin Panel" for admin.

    # Let's show basic stats to everyone, and full stats to admin?
    # Requirement: "stats (active downloads)" - implies public or user facing.
    # Requirement: "Mere paas ek alag admin panel ui/ux me aana chahiye... kitne users..."

    # If user is admin, show Admin Panel with "Users" button.
    # If normal user, show basic stats.

    if callback.from_user.id == Config.ADMIN_ID:
        # Admin View
        total_users = await db.col.count_documents({})
        disk = shutil.disk_usage("/")

        text = (
            f"**Admin Stats Panel**\n\n"
            f"👥 Total Users: {total_users}\n"
            f"💾 Disk Free: {disk.free // (1024**3)} GB\n"
            f"🧠 RAM Usage: {psutil.virtual_memory().percent}%\n"
        )

        buttons = InlineKeyboardMarkup([
            [InlineKeyboardButton("📜 Users List", callback_data="list_users")],
            [InlineKeyboardButton("🔙 Back", callback_data="back_home")]
        ])

        await callback.message.edit_text(text, reply_markup=buttons)
    else:
        # User View (just active downloads - mocked for now as we don't have a global counter yet)
        # Assuming we track active downloads in a variable or DB.
        # For now, placeholder.
        await callback.answer("Stats: Active Downloads: (Coming Soon)", show_alert=True)

@app.on_callback_query(filters.regex("list_users"))
async def list_users_cb(client: Client, callback: CallbackQuery):
    if callback.from_user.id != Config.ADMIN_ID:
        return

    users_cursor = await db.get_all_users()
    users = await users_cursor.to_list(length=50) # Limit to 50 for now

    text = "**User List (Last 50):**\n\n"
    for user in users:
        uid = user.get('id')
        name = f"User {uid}" # We might not have names if not stored, let's assume we just use ID
        # Make name clickable to profile
        text += f"• [{name}](tg://user?id={uid}) (`{uid}`)\n"

    await callback.message.edit_text(text, reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Back", callback_data="stats")]]))
