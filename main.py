# main.py — DREAM GIRL BOT COMPLETE
import os, io, json, uuid, asyncio, logging, random
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()

import google.generativeai as genai
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ApplicationBuilder, CommandHandler,
    MessageHandler, filters, ContextTypes
)
from vc_core import (
    join_vc, leave_vc, speak_in_vc,
    start_vc_system, stop_vc_system,
    sync_voices, make_tts_ogg, active_vc_chats,
)
from voice_chat import handle_voice_message

logging.basicConfig(
    format="%(asctime)s — %(levelname)s — %(message)s",
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# ── ENV ───────────────────────────────────────────────────
BOT_TOKEN      = os.getenv("BOT_TOKEN", "")
ADMIN_ID       = int(os.getenv("ADMIN_ID", "0"))
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")

genai.configure(api_key=GEMINI_API_KEY)
gemini_model = genai.GenerativeModel("gemini-1.5-flash")
DATA_FILE    = "data.json"

# ── DATA ──────────────────────────────────────────────────
settings = {
    "start_photos":    [],
    "start_caption":   "🌸 *Dream Girl Bot mein aapka swagat hai!*\nMera naam lo aur kuch bhi pucho~",
    "start_buttons":   [],
    "auto_replies":    {},
    "voice_messages":  {},
    "coupons":        {},
    "top_banners":    {},
    "status_caption": "Bot is running smoothly!",
}
chat_enabled   = {}
daily_claimed  = {}
weekly_claimed = {}
user_data      = {}
group_data     = {}

def load_data():
    global settings, chat_enabled, daily_claimed, weekly_claimed, user_data, group_data
    try:
        with open(DATA_FILE, "r") as f:
            d = json.load(f)
            settings.update(d.get("settings", {}))
            chat_enabled   = d.get("chat_enabled", {})
            daily_claimed  = d.get("daily_claimed", {})
            weekly_claimed = d.get("weekly_claimed", {})
            user_data      = d.get("user_data", {})
            group_data     = d.get("group_data", {})
    except:
        pass
    sync_voices(settings.get("voice_messages", {}))

def save_data():
    with open(DATA_FILE, "w") as f:
        json.dump({
            "settings": settings,
            "chat_enabled": chat_enabled,
            "daily_claimed": daily_claimed,
            "weekly_claimed": weekly_claimed,
            "user_data": user_data,
            "group_data": group_data,
        }, f, ensure_ascii=False, indent=2)

# ── HELPERS ───────────────────────────────────────────────
async def is_admin_or_owner(update: Update) -> bool:
    user = update.effective_user
    if user.id == ADMIN_ID:
        return True
    chat = update.effective_chat
    if chat.type in ("group", "supergroup"):
        member = await chat.get_member(user.id)
        return member.status in ("administrator", "creator")
    return False

async def get_ai_response(text: str, name: str, user_id: int) -> str:
    try:
        prompt = (
            f"Tum Dream Girl ho ek cute friendly Hinglish AI bot. "
            f"User ka naam {name} hai. "
            f"Short cute warm reply do 1 ya 2 sentences mein. "
            f"User ne kaha: {text}"
        )
        resp = await asyncio.to_thread(gemini_model.generate_content, prompt)
        return resp.text.strip()
    except Exception as e:
        logger.error(f"[AI] {e}")
        return "Mujhe samajh nahi aaya~ Dobara try karo!"

def get_user_record(user_id: int) -> dict:
    uid = str(user_id)
    if uid not in user_data:
        user_data[uid] = {"coins": 0, "cats": {}, "family": "", "joined": str(datetime.now())}
    return user_data[uid]

# ══════════════════════════════════════════════════════════
#   COMMANDS
# ══════════════════════════════════════════════════════════

async def start_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user    = update.effective_user
    get_user_record(user.id)
    caption = settings.get("start_caption", "🌸 Welcome!")
    buttons = settings.get("start_buttons", [])
    keyboard = [[InlineKeyboardButton(b["name"], url=b["url"])] for b in buttons]
    markup   = InlineKeyboardMarkup(keyboard) if keyboard else None
    photos   = settings.get("start_photos", [])
    if photos:
        await update.message.reply_photo(
            photo=random.choice(photos)["file_id"],
            caption=caption, parse_mode="Markdown", reply_markup=markup
        )
    else:
        await update.message.reply_text(caption, parse_mode="Markdown", reply_markup=markup)

async def help_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user     = update.effective_user
    is_admin = user.id == ADMIN_ID
    user_text = (
        "╔══════════════════════╗\n"
        "     🌸 *DREAM GIRL BOT*\n"
        "╚══════════════════════╝\n\n"
        "🆕 *Commands:*\n"
        "┣ `/start` — Bot start karo\n"
        "┣ `/profile` — Apni profile\n"
        "┣ `/daily` — Daily 💰 100-200 coins\n"
        "┣ `/weekly` — Weekly 💰 500-1000 coins\n"
        "┣ `/coupon <code>` — Coupon se coins\n"
        "┣ `/top` — Leaderboard\n"
        "┣ `/gfbf` — Aaj ke BF GF\n"
        "┣ `/bff` — Aaj ke BFF\n"
        "┣ `/chaton` — Chat ON\n"
        "┣ `/chatoff` — Chat OFF\n"
        "┣ `/joinvc` — Dream Girl VC join kare\n"
        "┗ `/leavevc` — Dream Girl VC leave kare\n"
    )
    await update.message.reply_text(user_text, parse_mode="Markdown")
    if is_admin:
        admin_text = (
            "╔══════════════════════╗\n"
            "      🔑 *ADMIN PANEL*\n"
            "╚══════════════════════╝\n\n"
            "┣ `/broadcast` — Sabko message\n"
            "┣ `/setphoto` — Start photo\n"
            "┣ `/photolist` — Photos list\n"
            "┣ `/resetpic <id>` — Photo hatao\n"
            "┣ `/setcaption <text>` — Caption\n"
            "┣ `/setbutton NAME url` — Button\n"
            "┣ `/setreply kw | reply` — Auto reply\n"
            "┣ `/delreply <kw>` — Reply hatao\n"
            "┣ `/listreplies` — Replies list\n"
            "┣ `/uploadVoice <kw>` — Voice upload\n"
            "┣ `/revoice <id>` — Voice hatao\n"
            "┣ `/vlist` — Voices list\n"
            "┣ `/addcoupon CODE coins [uses]` — Coupon\n"
            "┣ `/delcoupon CODE` — Coupon hatao\n"
            "┣ `/status` — Bot status\n"
            "┣ `/userlist` — Users file\n"
            "┗ `/grouplist` — Groups file\n"
        )
        await update.message.reply_text(admin_text, parse_mode="Markdown")

async def joinvc_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await is_admin_or_owner(update):
        await update.message.reply_text("Sirf admins VC join kara sakte hain.")
        return
    chat_id = update.effective_chat.id
    msg     = await update.message.reply_text("VC join kar rahi hoon...")
    success = await join_vc(chat_id, bot_app=context.bot, ai_func=get_ai_response)
    if success:
        await msg.edit_text("Dream Girl VC mein aa gayi! Mera naam lo aur kuch bhi pucho~")
    else:
        await msg.edit_text(
            "VC join nahi ho saka.\n\n"
            "Check karo:\n"
            "• Group mein Voice Chat active hai?\n"
            "• Bot admin hai?\n"
            "• API_ID aur API_HASH sahi hain .env mein?"
        )

async def leavevc_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await is_admin_or_owner(update):
        await update.message.reply_text("Sirf admins VC leave kara sakte hain.")
        return
    success = await leave_vc(update.effective_chat.id)
    if success:
        await update.message.reply_text("Dream Girl VC se nikal gayi~ Phir milenge!")
    else:
        await update.message.reply_text("Bot VC mein nahi hai.")

async def daily_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user  = update.effective_user
    uid   = str(user.id)
    today = datetime.now().strftime("%Y-%m-%d")
    if daily_claimed.get(uid) == today:
        await update.message.reply_text("Aaj ka daily reward le liya! Kal wapas aana~")
        return
    coins = random.randint(100, 200)
    rec   = get_user_record(user.id)
    rec["coins"] += coins
    daily_claimed[uid] = today
    save_data()
    await update.message.reply_text(f"Daily reward mila! +{coins} coins\nTotal: {rec['coins']} coins")

async def weekly_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    uid  = str(user.id)
    now  = datetime.now()
    last = weekly_claimed.get(uid)
    if last:
        last_dt = datetime.strptime(last, "%Y-%m-%d")
        if (now - last_dt).days < 7:
            rem = 7 - (now - last_dt).days
            await update.message.reply_text(f"Weekly reward ke liye {rem} din aur wait karo!")
            return
    coins = random.randint(500, 1000)
    rec   = get_user_record(user.id)
    rec["coins"] += coins
    weekly_claimed[uid] = now.strftime("%Y-%m-%d")
    save_data()
    await update.message.reply_text(f"Weekly reward mila! +{coins} coins\nTotal: {rec['coins']} coins")

async def coupon_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text("Usage: /coupon <code>")
        return
    code    = context.args[0].upper()
    coupons = settings.get("coupons", {})
    uid     = str(update.effective_user.id)
    if code not in coupons:
        await update.message.reply_text("Invalid coupon!")
        return
    c        = coupons[code]
    used_by  = c.get("used_by", [])
    max_uses = c.get("max_uses", 999)
    if uid in used_by:
        await update.message.reply_text("Yeh coupon tum pehle use kar chuke ho!")
        return
    if len(used_by) >= max_uses:
        await update.message.reply_text("Coupon expire ho gaya!")
        return
    coins = c["coins"]
    rec   = get_user_record(update.effective_user.id)
    rec["coins"] += coins
    used_by.append(uid)
    c["used_by"] = used_by
    save_data()
    await update.message.reply_text(f"Coupon redeemed! +{coins} coins\nTotal: {rec['coins']} coins")

async def profile_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    rec  = get_user_record(user.id)
    text = (
        f"*{user.first_name} ki Profile*\n\n"
        f"Coins: `{rec.get('coins', 0)}`\n"
        f"Cats: `{len(rec.get('cats', {}))}`\n"
        f"Family: `{rec.get('family', 'N/A')}`\n"
        f"Joined: `{rec.get('joined', 'N/A')[:10]}`"
    )
    await update.message.reply_text(text, parse_mode="Markdown")

async def top_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    banner  = settings.get("top_banners", {}).get("top")
    sorted_ = sorted(user_data.items(), key=lambda x: x[1].get("coins", 0), reverse=True)[:10]
    medals  = ["1","2","3","4","5","6","7","8","9","10"]
    text    = "*Top 10 Leaderboard*\n\n"
    for i, (uid, data) in enumerate(sorted_):
        text += f"{medals[i]}. `{uid}` — {data.get('coins', 0)} coins\n"
    if banner:
        await update.message.reply_photo(photo=banner, caption=text, parse_mode="Markdown")
    else:
        await update.message.reply_text(text, parse_mode="Markdown")

async def gfbf_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Aaj ke BF GF abhi decide nahi hue~ Thodi der mein try karo!")

async def bff_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Aaj ke BFF abhi decide nahi hue~ Thodi der mein try karo!")

async def chaton_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await is_admin_or_owner(update): return
    chat_enabled[str(update.effective_chat.id)] = True
    save_data()
    await update.message.reply_text("Chat ON!")

async def chatoff_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await is_admin_or_owner(update): return
    chat_enabled[str(update.effective_chat.id)] = False
    save_data()
    await update.message.reply_text("Chat OFF!")

# ── Admin ─────────────────────────────────────────────────

async def setphoto_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID: return
    if not update.message.reply_to_message or not update.message.reply_to_message.photo:
        await update.message.reply_text("Photo reply mein bhejo!")
        return
    fid = update.message.reply_to_message.photo[-1].file_id
    pid = str(uuid.uuid4())[:8]
    settings["start_photos"].append({"file_id": fid, "id": pid})
    save_data()
    await update.message.reply_text(f"Photo added! ID: `{pid}`", parse_mode="Markdown")

async def photolist_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID: return
    photos = settings.get("start_photos", [])
    if not photos:
        await update.message.reply_text("Koi photo nahi.")
        return
    text = "*Photos:*\n" + "\n".join(f"• `{p['id']}`" for p in photos)
    await update.message.reply_text(text, parse_mode="Markdown")

async def resetpic_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID: return
    if not context.args:
        await update.message.reply_text("Usage: /resetpic <id>")
        return
    pid = context.args[0]
    settings["start_photos"] = [p for p in settings["start_photos"] if p["id"] != pid]
    save_data()
    await update.message.reply_text("Photo removed!")

async def setcaption_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID: return
    text = " ".join(context.args)
    if not text:
        await update.message.reply_text("Usage: /setcaption <text>")
        return
    settings["start_caption"] = text
    save_data()
    await update.message.reply_text("Caption set!")

async def setbutton_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID: return
    if len(context.args) < 2:
        await update.message.reply_text("Usage: /setbutton NAME url")
        return
    settings["start_buttons"].append({"name": context.args[0], "url": context.args[1]})
    save_data()
    await update.message.reply_text("Button added!")

async def setreply_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID: return
    text = update.message.text.split(None, 1)[1] if len(update.message.text.split()) > 1 else ""
    if "|" not in text:
        await update.message.reply_text("Usage: /setreply keyword | reply")
        return
    kw, reply = text.split("|", 1)
    settings["auto_replies"][kw.strip()] = reply.strip()
    save_data()
    await update.message.reply_text(f"Auto reply set: `{kw.strip()}`", parse_mode="Markdown")

async def delreply_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID: return
    kw = " ".join(context.args)
    if kw in settings["auto_replies"]:
        del settings["auto_replies"][kw]
        save_data()
        await update.message.reply_text("Deleted!")
    else:
        await update.message.reply_text("Keyword nahi mila.")

async def listreplies_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID: return
    ar = settings.get("auto_replies", {})
    if not ar:
        await update.message.reply_text("Koi auto reply nahi.")
        return
    text = "*Auto Replies:*\n" + "\n".join(f"• `{k}` → {v}" for k, v in ar.items())
    await update.message.reply_text(text, parse_mode="Markdown")

async def uploadvoice_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID: return
    if not context.args:
        await update.message.reply_text("Usage: /uploadVoice <keyword>")
        return
    if not update.message.reply_to_message or not update.message.reply_to_message.voice:
        await update.message.reply_text("Voice reply mein bhejo!")
        return
    kw  = " ".join(context.args).lower()
    fid = update.message.reply_to_message.voice.file_id
    vid = str(uuid.uuid4())[:8]
    settings["voice_messages"][vid] = {"keyword": kw, "file_id": fid, "id": vid}
    sync_voices(settings["voice_messages"])
    save_data()
    await update.message.reply_text(f"Voice saved! Keyword: `{kw}` ID: `{vid}`", parse_mode="Markdown")

async def revoice_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID: return
    if not context.args:
        await update.message.reply_text("Usage: /revoice <id>")
        return
    vid = context.args[0]
    if vid in settings["voice_messages"]:
        del settings["voice_messages"][vid]
        sync_voices(settings["voice_messages"])
        save_data()
        await update.message.reply_text("Deleted!")
    else:
        await update.message.reply_text("ID nahi mila.")

async def vlist_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID: return
    vm = settings.get("voice_messages", {})
    if not vm:
        await update.message.reply_text("Koi voice nahi.")
        return
    text = "*Voices:*\n" + "\n".join(f"• `{vid}` — `{vd['keyword']}`" for vid, vd in vm.items())
    await update.message.reply_text(text, parse_mode="Markdown")

async def addcoupon_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID: return
    if len(context.args) < 2:
        await update.message.reply_text("Usage: /addcoupon CODE coins [uses]")
        return
    code     = context.args[0].upper()
    coins    = int(context.args[1])
    max_uses = int(context.args[2]) if len(context.args) > 2 else 999
    settings["coupons"][code] = {"coins": coins, "max_uses": max_uses, "used_by": []}
    save_data()
    await update.message.reply_text(f"Coupon `{code}` created! {coins} coins.", parse_mode="Markdown")

async def delcoupon_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID: return
    if not context.args:
        await update.message.reply_text("Usage: /delcoupon CODE")
        return
    code = context.args[0].upper()
    if code in settings["coupons"]:
        del settings["coupons"][code]
        save_data()
        await update.message.reply_text("Deleted!")
    else:
        await update.message.reply_text("Coupon nahi mila.")

async def broadcast_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID: return
    if not update.message.reply_to_message:
        await update.message.reply_text("Broadcast message reply mein bhejo!")
        return
    msg = update.message.reply_to_message
    ok  = 0; fail = 0
    for uid in user_data:
        try:
            await msg.forward(int(uid))
            ok += 1
            await asyncio.sleep(0.05)
        except:
            fail += 1
    await update.message.reply_text(f"Broadcast done! {ok} success, {fail} failed")

async def status_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID: return
    text = (
        f"*Bot Status*\n\n"
        f"{settings.get('status_caption', '')}\n\n"
        f"Users: `{len(user_data)}`\n"
        f"Groups: `{len(group_data)}`\n"
        f"Active VCs: `{len(active_vc_chats)}`"
    )
    await update.message.reply_text(text, parse_mode="Markdown")

async def userlist_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID: return
    data = "\n".join(user_data.keys()).encode()
    await update.message.reply_document(document=io.BytesIO(data), filename="users.txt")

async def grouplist_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID: return
    data = "\n".join(group_data.keys()).encode()
    await update.message.reply_document(document=io.BytesIO(data), filename="groups.txt")

# ── Message Handlers ─────────────────────────────────────

async def handle_text_msg(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    chat = update.effective_chat
    msg  = update.message
    if not user or not msg or not msg.text:
        return
    get_user_record(user.id)
    cid = str(chat.id)
    if chat.type in ("group", "supergroup"):
        group_data[cid] = {"title": chat.title}
        if not chat_enabled.get(cid, True):
            return
    for kw, reply in settings.get("auto_replies", {}).items():
        if kw.lower() in msg.text.lower():
            await msg.reply_text(reply)
            return
    if chat.type in ("private", "group", "supergroup"):
        display  = user.first_name or "Pyaare"
        response = await get_ai_response(msg.text, display, user.id)
        if int(cid) in active_vc_chats:
            await speak_in_vc(int(cid), response)
        await msg.reply_text(f"🌸 {response}")

async def handle_voice_msg(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    chat = update.effective_chat
    if not user: return
    if chat.type in ("group", "supergroup") and not chat_enabled.get(str(chat.id), True):
        return
    await handle_voice_message(update, context, settings, ai_func=get_ai_response)

# ══════════════════════════════════════════════════════════
#   MAIN
# ══════════════════════════════════════════════════════════

async def main():
    load_data()
    try:
        await start_vc_system()
        logger.info("VC system ready!")
    except Exception as e:
        logger.error(f"VC system error: {e}")

    app = ApplicationBuilder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start",        start_cmd))
    app.add_handler(CommandHandler("help",         help_cmd))
    app.add_handler(CommandHandler("joinvc",       joinvc_cmd))
    app.add_handler(CommandHandler("leavevc",      leavevc_cmd))
    app.add_handler(CommandHandler("daily",        daily_cmd))
    app.add_handler(CommandHandler("weekly",       weekly_cmd))
    app.add_handler(CommandHandler("coupon",       coupon_cmd))
    app.add_handler(CommandHandler("profile",      profile_cmd))
    app.add_handler(CommandHandler("top",          top_cmd))
    app.add_handler(CommandHandler("gfbf",         gfbf_cmd))
    app.add_handler(CommandHandler("bff",          bff_cmd))
    app.add_handler(CommandHandler("chaton",       chaton_cmd))
    app.add_handler(CommandHandler("chatoff",      chatoff_cmd))
    app.add_handler(CommandHandler("setphoto",     setphoto_cmd))
    app.add_handler(CommandHandler("photolist",    photolist_cmd))
    app.add_handler(CommandHandler("resetpic",     resetpic_cmd))
    app.add_handler(CommandHandler("setcaption",   setcaption_cmd))
    app.add_handler(CommandHandler("setbutton",    setbutton_cmd))
    app.add_handler(CommandHandler("setreply",     setreply_cmd))
    app.add_handler(CommandHandler("delreply",     delreply_cmd))
    app.add_handler(CommandHandler("listreplies",  listreplies_cmd))
    app.add_handler(CommandHandler("uploadVoice",  uploadvoice_cmd))
    app.add_handler(CommandHandler("revoice",      revoice_cmd))
    app.add_handler(CommandHandler("vlist",        vlist_cmd))
    app.add_handler(CommandHandler("addcoupon",    addcoupon_cmd))
    app.add_handler(CommandHandler("delcoupon",    delcoupon_cmd))
    app.add_handler(CommandHandler("broadcast",    broadcast_cmd))
    app.add_handler(CommandHandler("status",       status_cmd))
    app.add_handler(CommandHandler("userlist",     userlist_cmd))
    app.add_handler(CommandHandler("grouplist",    grouplist_cmd))
    app.add_handler(MessageHandler(filters.VOICE, handle_voice_msg))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text_msg))

    logger.info("Bot starting...")
    try:
        await app.initialize()
        await app.start()
        await app.updater.start_polling(drop_pending_updates=True)
        await asyncio.Event().wait()
    finally:
        await app.updater.stop()
        await app.stop()
        await app.shutdown()
        await stop_vc_system()

if __name__ == "__main__":
    asyncio.run(main())
