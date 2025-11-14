import logging
from pyrogram import Client, filters
from pyrogram.errors import UserNotParticipant, ChatAdminRequired, PeerIdInvalid, FloodWait
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery
from pyrogram.raw import functions
import asyncio
from config import ENABLE_FSUB, FSUB
from bot import Bot

log = logging.getLogger(__name__)


# ===================== DYNAMIC FSUB LOADING =====================
def load_fsub():
    """
    Parses FSUB only once and mutates the existing FSUB dictionary
    without overwriting the imported reference.
    """
    if not ENABLE_FSUB or not FSUB:
        log.info("ℹ️ FSUB disabled or empty.")
        return

    try:
        # Copy raw list (e.g. ["ABC: -10012345", "DEF: -100999"])
        raw_list = FSUB.copy() if isinstance(FSUB, list) else []

        # Replace FSUB (dict) contents safely
        FSUB = {}

        for item in raw_list:
            if ":" in item:
                name, cid = item.split(":", 1)
                FSUB[name.strip()] = int(cid.strip())

        log.info(f"🔍 FSUB loaded: {FSUB}")

    except Exception as e:
        log.error(f"⚠️ FSUB parsing error: {e}")
        FSUB.clear()


# Load FSUB at import time
load_fsub()



# ===================== SAFE CHANNEL RESOLVE =====================
async def safe_resolve_channel(client: Client, channel_id: int):
    try:
        peer = await client.resolve_peer(channel_id)
        await client.invoke(functions.channels.GetFullChannel(channel=peer))
        return True

    except PeerIdInvalid:
        try:
            await client.invoke(functions.channels.GetChannels(id=[channel_id]))
            return True
        except Exception:
            return False

    except FloodWait as e:
        await asyncio.sleep(e.value)
        return await safe_resolve_channel(client, channel_id)

    except Exception:
        return False



# ===================== FORCE SUB CHECK =====================
async def check_force_sub(client: Client, user_id: int, message) -> bool:
    if not ENABLE_FSUB or not FSUB:
        return True  # FSUB disabled

    not_joined = []

    for btn_name, channel_id in FSUB.items():
        try:
            member = await client.get_chat_member(channel_id, user_id)
            if member.status in ("left", "kicked"):
                not_joined.append((btn_name, channel_id))

        except PeerIdInvalid:
            ok = await safe_resolve_channel(client, channel_id)
            if not ok:
                await message.reply_text(
                    f"❌ Bot cannot access `{btn_name}` ({channel_id}).\n"
                    f"Please re-add the bot as admin."
                )
                return False

            member = await client.get_chat_member(channel_id, user_id)
            if member.status in ("left", "kicked"):
                not_joined.append((btn_name, channel_id))

        except UserNotParticipant:
            not_joined.append((btn_name, channel_id))

        except ChatAdminRequired:
            await message.reply_text(f"⚠️ Bot must be admin in {btn_name} channel.")
            return False

        except Exception as e:
            log.error(f"⚠️ Error checking {channel_id}: {e}")
            return False

    if not not_joined:
        return True  # All good

    # --- BUTTONS ---
    buttons = []
    row = []

    for i, (name, cid) in enumerate(not_joined, start=1):
        try:
            invite = await client.create_chat_invite_link(cid)
            url = invite.invite_link
        except Exception:
            url = "https://t.me"

        row.append(InlineKeyboardButton(f"• {name} •", url=url))

        if i % 2 == 0:
            buttons.append(row)
            row = []

    if row:
        buttons.append(row)

    buttons.append(
        [InlineKeyboardButton("✅ I Joined", callback_data="fsub_check")]
    )

    await message.reply_text(
        "⚠️ Please join all required channels to use this bot:",
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
            "✅ Thank you! You have unlocked all bot features.\n\nSend /start again."
        )