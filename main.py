# main.py -- Dream Girl Bot
import os, asyncio, logging, json, io
from telegram import (
    Update, InlineKeyboardButton, InlineKeyboardMarkup, BotCommand
)
from telegram.ext import (
    Application, CommandHandler, MessageHandler,
    filters, ContextTypes, ConversationHandler,
    CallbackQueryHandler
)
from vc_core import (
    join_vc, leave_vc, start_vc_system, stop_vc_system,
    make_tts_ogg, active_vc_chats, speak_in_vc,
    add_assistant, remove_assistant, stt_from_bytes
)
import google.generativeai as genai

logging.basicConfig(
    format="%(asctime)s — %(levelname)s — %(message)s",
    level=logging.INFO
)
logger = logging.getLogger(__name__)

BOT_TOKEN  = os.getenv("BOT_TOKEN", "")
ADMIN_ID   = int(os.getenv("ADMIN_ID", "0"))
GEMINI_KEY = os.getenv("GEMINI_API_KEY", "")
BOT_NAME   = os.getenv("BOT_USERNAME", "IamYourGirlBot")

genai.configure(api_key=GEMINI_KEY)
gemini = genai.GenerativeModel("gemini-1.5-flash")

DATA_FILE = "data.json"


def load_data():
    try:
        with open(DATA_FILE, "r") as f:
            return json.load(f)
    except:
        return {
            "welcome_photo": "",
            "welcome_caption": "Hiii! Main hoon Dream Girl 🌸",
            "welcome_buttons": [],
            "welcome_photos": [],
            "leaderboard_photo": "",
            "chat_disabled": [],
            "group_msg_count": {},
            "users": []
        }


def save_data(d):
    with open(DATA_FILE, "w") as f:
        json.dump(d, f, indent=2, ensure_ascii=False)


data = load_data()

AWAIT_BUTTON_NAME, AWAIT_BUTTON_URL, AWAIT_DPHOTO_INDEX = range(3)


def is_admin(uid: int) -> bool:
    return uid == ADMIN_ID


async def get_ai_response(text: str, name: str, uid: int) -> str:
    try:
        prompt = (
            f"Tum ho Dream Girl — ek cute, pyaari, real ladki ki tarah baat "
            f"karne wali AI girlfriend. Sirf Hinglish mein baat karo "
            f"(Hindi + thodi English). Har jawab short, warm aur natural hona "
            f"chahiye jaise ek close girlfriend baat karti hai. Kabhi robot "
            f"jaisi baat mat karo. User ka naam hai {name}. "
            f"Unka message: {text}"
        )
        resp = gemini.generate_content(prompt)
        return resp.text.strip()
    except Exception as e:
        logger.error(f"[AI] {e}")
        return "Hiii~ Kuch toh hua, thoda baad mein baat karte hain na? 🌸"


def track_group(cid: str, title: str):
    data.setdefault("group_msg_count", {})
    if cid not in data["group_msg_count"]:
        data["group_msg_count"][cid] = {"count": 0, "title": title}
    data["group_msg_count"][cid]["count"] += 1
    data["group_msg_count"][cid]["title"] = title
    save_data(data)


# ── /start ────────────────────────────────────────────────
async def cmd_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    if user:
        uid = str(user.id)
        if uid not in data.get("users", []):
            data.setdefault("users", []).append(uid)
            save_data(data)

    caption = data.get("welcome_caption", "Hiii! Main hoon Dream Girl 🌸")
    buttons = data.get("welcome_buttons", [])
    photos  = data.get("welcome_photos", [])
    if not photos and data.get("welcome_photo"):
        photos = [data["welcome_photo"]]

    kb = []
    row = []
    for i, btn in enumerate(buttons):
        row.append(InlineKeyboardButton(btn["name"], url=btn["url"]))
        if len(row) == 2 or i == len(buttons) - 1:
            kb.append(row)
            row = []
    markup = InlineKeyboardMarkup(kb) if kb else None

    if photos:
        try:
            await update.message.reply_photo(
                photo=photos[0], caption=caption,
                reply_markup=markup, parse_mode="Markdown"
            )
            return
        except:
            pass
    await update.message.reply_text(caption, reply_markup=markup, parse_mode="Markdown")


# ── /gfbf ─────────────────────────────────────────────────
async def cmd_gfbf(update: Update, context: ContextTypes.DEFAULT_TYPE):
    args = context.args
    if len(args) < 2:
        await update.message.reply_text("📝 Usage: `/gfbf [GF naam] [BF naam]`", parse_mode="Markdown")
        return
    gf, bf = args[0], args[1]
    await update.message.reply_text(
        f"💑 *GF / BF Card*\n────────────────────\n"
        f"💗 GF: *{gf}*\n💙 BF: *{bf}*\n"
        f"────────────────────\nMade with ❤️ by @{BOT_NAME}",
        parse_mode="Markdown"
    )


# ── /bff ──────────────────────────────────────────────────
async def cmd_bff(update: Update, context: ContextTypes.DEFAULT_TYPE):
    args = context.args
    if len(args) < 2:
        await update.message.reply_text("📝 Usage: `/bff [naam1] [naam2]`", parse_mode="Markdown")
        return
    a, b = args[0], args[1]
    await update.message.reply_text(
        f"👯 *BFF Card*\n────────────────────\n"
        f"🌟 BFF 1: *{a}*\n🌟 BFF 2: *{b}*\n"
        f"────────────────────\nMade with 💛 by @{BOT_NAME}",
        parse_mode="Markdown"
    )


# ── /couple ───────────────────────────────────────────────
async def cmd_couple(update: Update, context: ContextTypes.DEFAULT_TYPE):
    args = context.args
    if len(args) < 2:
        await update.message.reply_text("📝 Usage: `/couple [naam1] [naam2]`", parse_mode="Markdown")
        return
    a, b = args[0], args[1]
    await update.message.reply_text(
        f"💞 *Couple Card*\n────────────────────\n"
        f"🌹 {a} ❤️ {b}\n"
        f"────────────────────\nMade with 💕 by @{BOT_NAME}",
        parse_mode="Markdown"
    )


# ── /setphoto ─────────────────────────────────────────────
async def cmd_setphoto(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id):
        await update.message.reply_text("❌ Sirf admin kar sakta hai.")
        return
    if update.message.photo:
        fid = update.message.photo[-1].file_id
        data["welcome_photo"] = fid
        data["welcome_photos"] = [fid]
        save_data(data)
        await update.message.reply_text("✅ Welcome photo set ho gaya!")
    else:
        await update.message.reply_text("📸 Photo ke saath /setphoto bhejo.")


# ── /addphoto ─────────────────────────────────────────────
async def cmd_addphoto(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id):
        await update.message.reply_text("❌ Sirf admin kar sakta hai.")
        return
    if update.message.photo:
        fid = update.message.photo[-1].file_id
        data.setdefault("welcome_photos", []).append(fid)
        save_data(data)
        await update.message.reply_text(f"✅ Photo add ho gayi! Total: {len(data['welcome_photos'])}")
    else:
        await update.message.reply_text("📸 Photo ke saath /addphoto bhejo.")


# ── /dphoto ───────────────────────────────────────────────
async def cmd_dphoto(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id):
        await update.message.reply_text("❌ Sirf admin kar sakta hai.")
        return
    photos = data.get("welcome_photos", [])
    if not photos:
        await update.message.reply_text("Koi photo nahi hai.")
        return ConversationHandler.END
    lines = "\n".join([f"{i+1}. Photo {i+1}" for i in range(len(photos))])
    await update.message.reply_text(f"Kaunsi photo delete karni hai? Number bhejo:\n{lines}")
    return AWAIT_DPHOTO_INDEX


async def dphoto_index(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        idx = int(update.message.text.strip()) - 1
        photos = data.get("welcome_photos", [])
        if 0 <= idx < len(photos):
            photos.pop(idx)
            data["welcome_photos"] = photos
            data["welcome_photo"] = photos[0] if photos else ""
            save_data(data)
            await update.message.reply_text("✅ Photo delete ho gayi!")
        else:
            await update.message.reply_text("❌ Galat number.")
    except:
        await update.message.reply_text("❌ Number sahi se bhejo.")
    return ConversationHandler.END


# ── /setcaption ───────────────────────────────────────────
async def cmd_setcaption(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id):
        await update.message.reply_text("❌ Sirf admin kar sakta hai.")
        return
    text = " ".join(context.args)
    if not text:
        await update.message.reply_text("📝 Usage: `/setcaption [caption]`", parse_mode="Markdown")
        return
    data["welcome_caption"] = text
    save_data(data)
    await update.message.reply_text(f"✅ Caption set:\n{text}")


# ── /addbutton ────────────────────────────────────────────
async def cmd_addbutton(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id):
        await update.message.reply_text("❌ Sirf admin kar sakta hai.")
        return
    await update.message.reply_text("Button ka naam bhejo:")
    return AWAIT_BUTTON_NAME


async def addbutton_name(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["btn_name"] = update.message.text.strip()
    await update.message.reply_text("Ab button ka URL bhejo:")
    return AWAIT_BUTTON_URL


async def addbutton_url(update: Update, context: ContextTypes.DEFAULT_TYPE):
    url  = update.message.text.strip()
    name = context.user_data.get("btn_name", "Button")
    data.setdefault("welcome_buttons", []).append({"name": name, "url": url})
    save_data(data)
    await update.message.reply_text(f"✅ Button add ho gaya!\nNaam: {name}\nURL: {url}")
    return ConversationHandler.END


# ── /delbutton ────────────────────────────────────────────
async def cmd_delbutton(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id):
        await update.message.reply_text("❌ Sirf admin kar sakta hai.")
        return
    buttons = data.get("welcome_buttons", [])
    if not buttons:
        await update.message.reply_text("Koi button nahi hai.")
        return
    kb = [[InlineKeyboardButton(f"❌ {b['name']}", callback_data=f"delbtn_{i}")]
          for i, b in enumerate(buttons)]
    await update.message.reply_text("Kaunsa button delete karna hai?",
                                     reply_markup=InlineKeyboardMarkup(kb))


async def delbutton_cb(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    if not is_admin(q.from_user.id):
        return
    idx = int(q.data.split("_")[1])
    buttons = data.get("welcome_buttons", [])
    if 0 <= idx < len(buttons):
        name = buttons.pop(idx)["name"]
        data["welcome_buttons"] = buttons
        save_data(data)
        await q.edit_message_text(f"✅ Button '{name}' delete ho gaya!")


# ── /bcast ────────────────────────────────────────────────
async def cmd_bcast(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id):
        await update.message.reply_text("❌ Sirf admin kar sakta hai.")
        return
    text = " ".join(context.args)
    if not text:
        await update.message.reply_text("📝 Usage: `/bcast [message]`", parse_mode="Markdown")
        return
    users = data.get("users", [])
    sent = failed = 0
    for uid in users:
        try:
            await context.bot.send_message(int(uid), text)
            sent += 1
        except:
            failed += 1
    await update.message.reply_text(f"📢 Broadcast:\n✅ Sent: {sent}\n❌ Failed: {failed}")


# ── /chaton /chatoff ──────────────────────────────────────
async def cmd_chaton(update: Update, context: ContextTypes.DEFAULT_TYPE):
    cid = str(update.effective_chat.id)
    lst = data.setdefault("chat_disabled", [])
    if cid in lst:
        lst.remove(cid)
        save_data(data)
    await update.message.reply_text("✅ Chat ON! Main ab jawab dungi 💬")


async def cmd_chatoff(update: Update, context: ContextTypes.DEFAULT_TYPE):
    cid = str(update.effective_chat.id)
    lst = data.setdefault("chat_disabled", [])
    if cid not in lst:
        lst.append(cid)
        save_data(data)
    await update.message.reply_text("🔇 Chat OFF. Main chup rahungi.")


# ── /topgroups ────────────────────────────────────────────
async def cmd_topgroups(update: Update, context: ContextTypes.DEFAULT_TYPE):
    counts = data.get("group_msg_count", {})
    top = sorted(counts.items(), key=lambda x: x[1].get("count", 0), reverse=True)[:10]
    if not top:
        await update.message.reply_text("Abhi koi group data nahi hai.")
        return
    medals = ["🥇", "🥈", "🥉"] + [f"{i}." for i in range(4, 11)]
    lines = [f"{medals[i]} {info['title']}" for i, (_, info) in enumerate(top)]
    text = (
        f"🏆 *Top 10 Groups*\n"
        f"────────────────────\n"
        + "\n".join(lines) +
        f"\n────────────────────\n"
        f"Top 10 Via @{BOT_NAME}"
    )
    photo = data.get("leaderboard_photo", "")
    if photo:
        try:
            await update.message.reply_photo(photo=photo, caption=text, parse_mode="Markdown")
            return
        except:
            pass
    await update.message.reply_text(text, parse_mode="Markdown")


# ── /setlphoto ────────────────────────────────────────────
async def cmd_setlphoto(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id):
        await update.message.reply_text("❌ Sirf admin kar sakta hai.")
        return
    if update.message.photo:
        data["leaderboard_photo"] = update.message.photo[-1].file_id
        save_data(data)
        await update.message.reply_text("✅ Leaderboard photo set ho gaya!")
    else:
        await update.message.reply_text("📸 Photo ke saath /setlphoto bhejo.")


# ── /joinvc ───────────────────────────────────────────────
async def cmd_joinvc(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id):
        await update.message.reply_text("❌ Sirf admin kar sakta hai.")
        return
    await update.message.reply_text("🎤 VC join karne ki koshish kar rahi hoon...")
    ok = await join_vc(update.effective_chat.id, bot_app=context.application,
                       ai_func=get_ai_response)
    if ok:
        await update.message.reply_text("✅ Dream Girl VC mein aa gayi! 🎙️")
    else:
        await update.message.reply_text(
            "❌ VC join nahi ho saka.\n\n"
            "• Group mein Voice Chat active hai?\n"
            "• Bot admin hai?\n"
            "• PYROGRAM_SESSION ya /addasis session set hai?"
        )


# ── /leavevc ──────────────────────────────────────────────
async def cmd_leavevc(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id):
        await update.message.reply_text("❌ Sirf admin kar sakta hai.")
        return
    ok = await leave_vc(update.effective_chat.id)
    if ok:
        await update.message.reply_text("👋 Dream Girl VC se chali gayi!")
    else:
        await update.message.reply_text("Bot VC mein nahi thi.")


# ── /addasis ──────────────────────────────────────────────
async def cmd_addasis(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id):
        await update.message.reply_text("❌ Sirf admin kar sakta hai.")
        return
    session = " ".join(context.args).strip()
    if not session:
        await update.message.reply_text(
            "📝 Usage: `/addasis [session_string]`",
            parse_mode="Markdown"
        )
        return
    add_assistant(session)
    await update.message.reply_text("✅ Assistant session add ho gaya!")


# ── /removeasis ───────────────────────────────────────────
async def cmd_removeasis(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id):
        await update.message.reply_text("❌ Sirf admin kar sakta hai.")
        return
    remove_assistant()
    await update.message.reply_text("✅ Assistant session hata diya gaya.")


# ── Message Handlers ──────────────────────────────────────
async def handle_text_msg(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    chat = update.effective_chat
    msg  = update.message
    if not user or not msg or not msg.text:
        return

    cid = str(chat.id)

    if chat.type in ("group", "supergroup"):
        track_group(cid, chat.title or "Unknown")
        if cid in data.get("chat_disabled", []):
            return

    display  = user.first_name or "Pyaare"
    response = await get_ai_response(msg.text, display, user.id)

    if chat.id in active_vc_chats:
        await speak_in_vc(chat.id, response)

    await msg.reply_text(f"🌸 {response}")


async def handle_voice_msg(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    chat = update.effective_chat
    msg  = update.message
    if not user or not msg:
        return
    if chat.type in ("group", "supergroup") and \
       str(chat.id) in data.get("chat_disabled", []):
        return
    try:
        file        = await msg.voice.get_file()
        audio_bytes = await file.download_as_bytearray()
        text        = stt_from_bytes(bytes(audio_bytes)) or "Suno mujhe"
        display     = user.first_name or "Pyaare"
        response    = await get_ai_response(text, display, user.id)
        if chat.id in active_vc_chats:
            await speak_in_vc(chat.id, response)
        await msg.reply_text(f"🌸 {response}")
    except Exception as e:
        logger.error(f"[VOICE] {e}")


# ── Main ──────────────────────────────────────────────────
async def main():
    app = Application.builder().token(BOT_TOKEN).build()

    addbutton_conv = ConversationHandler(
        entry_points=[CommandHandler("addbutton", cmd_addbutton)],
        states={
            AWAIT_BUTTON_NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, addbutton_name)],
            AWAIT_BUTTON_URL:  [MessageHandler(filters.TEXT & ~filters.COMMAND, addbutton_url)],
        },
        fallbacks=[]
    )

    dphoto_conv = ConversationHandler(
        entry_points=[CommandHandler("dphoto", cmd_dphoto)],
        states={
            AWAIT_DPHOTO_INDEX: [MessageHandler(filters.TEXT & ~filters.COMMAND, dphoto_index)],
        },
        fallbacks=[]
    )

    app.add_handler(addbutton_conv)
    app.add_handler(dphoto_conv)
    app.add_handler(CallbackQueryHandler(delbutton_cb, pattern=r"^delbtn_"))

    for cmd, func in [
        ("start",      cmd_start),
        ("gfbf",       cmd_gfbf),
        ("bff",        cmd_bff),
        ("couple",     cmd_couple),
        ("setphoto",   cmd_setphoto),
        ("addphoto",   cmd_addphoto),
        ("setcaption", cmd_setcaption),
        ("setcaptoin", cmd_setcaption),
        ("delbutton",  cmd_delbutton),
        ("debutton",   cmd_delbutton),
        ("bcast",      cmd_bcast),
        ("chaton",     cmd_chaton),
        ("chatoff",    cmd_chatoff),
        ("topgroups",  cmd_topgroups),
        ("topgruops",  cmd_topgroups),
        ("setlphoto",  cmd_setlphoto),
        ("joinvc",     cmd_joinvc),
        ("leavevc",    cmd_leavevc),
        ("addasis",    cmd_addasis),
        ("removeasis", cmd_removeasis),
        ("aaddasis",   cmd_removeasis),
    ]:
        app.add_handler(CommandHandler(cmd, func))

    app.add_handler(MessageHandler(filters.VOICE, handle_voice_msg))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text_msg))

    await app.bot.set_my_commands([
        BotCommand("start",      "Bot shuru karo"),
        BotCommand("gfbf",       "GF/BF card banao"),
        BotCommand("bff",        "BFF card banao"),
        BotCommand("couple",     "Couple card banao"),
        BotCommand("topgroups",  "Top 10 groups leaderboard"),
        BotCommand("chaton",     "Chat reply ON"),
        BotCommand("chatoff",    "Chat reply OFF"),
        BotCommand("joinvc",     "VC join karo [admin]"),
        BotCommand("leavevc",    "VC leave karo [admin]"),
        BotCommand("setphoto",   "Welcome photo set [admin]"),
        BotCommand("addphoto",   "Photo add karo [admin]"),
        BotCommand("dphoto",     "Photo delete karo [admin]"),
        BotCommand("setcaption", "Welcome caption set [admin]"),
        BotCommand("addbutton",  "Button add karo [admin]"),
        BotCommand("delbutton",  "Button delete karo [admin]"),
        BotCommand("setlphoto",  "Leaderboard photo set [admin]"),
        BotCommand("bcast",      "Broadcast [admin]"),
        BotCommand("addasis",    "VC assistant add [admin]"),
        BotCommand("removeasis", "VC assistant hatao [admin]"),
    ])

    logger.info("Dream Girl Bot starting...")
    await start_vc_system()
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
