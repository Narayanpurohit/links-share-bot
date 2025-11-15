			
			



import logging
from pyrogram import Client, filters
from pyrogram.errors import UserNotParticipant, ChatAdminRequired, PeerIdInvalid, FloodWait
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery
from pyrogram.raw import functions
import asyncio
from config import ENABLE_FSUB,FSUB
from bot import Bot

log = logging.getLogger(__name__)







# ===================== FORCE SUB CHECK =====================
async def check_force_sub(client: Client, user_id: int, message) -> bool:
    ENABLE_FSUB, FSUB

    if not ENABLE_FSUB:
        return True  # skip if disabled

    not_joined = []

    for btn_name, channel_id in FSUB.items():
        try:
            member = await client.get_chat_member(channel_id, user_id)
            if member.status in ("left", "kicked"):
                not_joined.append((btn_name, channel_id))

        except PeerIdInvalid:
            log.warning(f"⚠️ PeerIdInvalid while checking {channel_id}, resolving...")
                return False
            # retry check
            try:
                member = await client.get_chat_member(channel_id, user_id)
                if member.status in ("left", "kicked"):
                    not_joined.append((btn_name, channel_id))
            except Exception as e:
                log.error(f"❌ Still failed after resolving {channel_id}: {e}")
                return False

        except UserNotParticipant:
            not_joined.append((btn_name, channel_id))
        except ChatAdminRequired:
            await message.reply_text("⚠️ Bot must be admin in all FSUB channels!")
            log.error(f"❌ Bot not admin in {channel_id}")
            return False
        except Exception as e:
            log.error(f"⚠️ Error checking FSUB for channel {channel_id}: {e}")
            return False

    if not not_joined:
        return True  # all joined

    # 🔹 Generate buttons
    buttons = []
    row = []
    for i, (btn_name, channel_id) in enumerate(not_joined, start=1):
        try:
            invite = await client.create_chat_invite_link(channel_id)
            row.append(InlineKeyboardButton(f"• {btn_name} •", url=invite.invite_link))
        except Exception as e:
            log.error(f"⚠️ Failed to create invite link for {channel_id}: {e}")
            row.append(InlineKeyboardButton(f"• {btn_name} •", url="https://t.me"))
        if i % 2 == 0:
            buttons.append(row)
            row = []
    if row:
        buttons.append(row)
    buttons.append([InlineKeyboardButton("• ✅ I Joined •", callback_data="fsub_check")])

    await message.reply_text(
        "⚠️ You must join the following channel(s) before using this bot:",
        reply_markup=InlineKeyboardMarkup(buttons)
    )
    return False


# ===================== CALLBACK =====================
@Bot.on_callback_query(filters.regex("fsub_check"))
async def recheck_force_sub(client, callback_query: CallbackQuery):
    user_id = callback_query.from_user.id
    ok = await check_force_sub(client, user_id, callback_query.message)
    if ok:
        await callback_query.message.edit_text(
            "✅ Thanks! You’ve unlocked the bot features.\n\nSend /start again."
        )

