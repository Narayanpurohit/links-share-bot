import os
import logging
from pyrogram import Client, filters
from pyrogram.errors import UserNotParticipant, ChatAdminRequired, PeerIdInvalid, FloodWait
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery
from bot import Bot

log = logging.getLogger(__name__)


# ===================== FSUB VARIABLES =====================
ENABLE_FSUB = bool(os.environ.get("ENABLE_FSUB", True))

# Your FSUB list
FSUB = {
    "Main Channel": -1002687789677,
    "Backup Channel": -1002758325935
}


# ===================== FORCE SUB CHECK =====================
async def check_force_sub(client: Client, user_id: int, message) -> bool:

    if not ENABLE_FSUB:
        return True  # FSUB disabled → skip

    not_joined = []

    for btn_name, channel_id in FSUB.items():
        try:
            member = await client.get_chat_member(channel_id, user_id)
            if member.status in ("left", "kicked"):
                not_joined.append((btn_name, channel_id))

        except UserNotParticipant:
            not_joined.append((btn_name, channel_id))

        except ChatAdminRequired:
            await message.reply_text("⚠️ Bot must be admin in FSUB channels!")
            return False

        except Exception as e:
            log.error(f"⚠️ Error checking FSUB for channel {channel_id}: {e}")
            return False

    if not not_joined:
        return True  # User joined everything

    # Buttons
    buttons = []
    row = []

    for i, (btn_name, channel_id) in enumerate(not_joined, start=1):
        try:
            invite = await client.create_chat_invite_link(channel_id)
            row.append(InlineKeyboardButton(f"{btn_name}", url=invite.invite_link))
        except:
            row.append(InlineKeyboardButton(f"{btn_name}", url="https://t.me"))
        
        if i % 2 == 0:
            buttons.append(row)
            row = []

    if row:
        buttons.append(row)

    buttons.append([InlineKeyboardButton("I Joined ✅", callback_data="fsub_check")])

    await message.reply_text(
        "⚠️ Please join the required channels to continue:",
        reply_markup=InlineKeyboardMarkup(buttons)
    )

    return False


# ===================== CALLBACK =====================
@Bot.on_callback_query(filters.regex("fsub_check"))
async def recheck_force_sub(client, cq: CallbackQuery):
    ok = await check_force_sub(client, cq.from_user.id, cq.message)
    if ok:
        await cq.message.edit_text("✅ Verified! Send /start again.")