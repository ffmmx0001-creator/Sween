import os, asyncio, logging, json, random, io, tempfile
from telegram import Update, BotCommand, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application, CommandHandler, MessageHandler,
    filters, ContextTypes, CallbackQueryHandler
)
from google import genai

logging.basicConfig(format="%(asctime)s - %(levelname)s - %(message)s", level=logging.INFO)
logger = logging.getLogger(__name__)

BOT_TOKEN  = os.getenv("BOT_TOKEN", "")
GEMINI_KEY = os.getenv("GEMINI_API_KEY", "")
OWNER_ID   = int(os.getenv("OWNER_ID", "0"))

gemini_client = genai.Client(api_key=GEMINI_KEY)

# ── Data ─────────────────────────────────────────────────────────────────────
DATA_DIR = "data"
os.makedirs(DATA_DIR, exist_ok=True)

def load_json(name, default):
    path = f"{DATA_DIR}/{name}.json"
    try:
        if os.path.exists(path):
            with open(path, "r", encoding="utf-8") as f:
                return json.load(f)
    except Exception:
        pass
    return default

def save_json(name, data):
    with open(f"{DATA_DIR}/{name}.json", "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

settings = load_json("settings", {
    "caption": "Hiii! Main hoon Dream Girl\nTumhari pyaari AI girlfriend!",
    "photos":  [],
    "owner_link": "https://t.me/SweenSpy",
    "gcap": "Top Groups jahan Dream Girl active hai!",
    "gpic": None,
    "chat_on": True
})
memory  = load_json("memory",  {})
gcounts = load_json("gcounts", {})
ginfo   = load_json("ginfo",   {})
members = load_json("members", {"users": [], "groups": []})

# ── Helpers ───────────────────────────────────────────────────────────────────
def is_owner(user_id: int) -> bool:
    return user_id == OWNER_ID

def add_member(chat_id: int, is_group: bool = False):
    key = "groups" if is_group else "users"
    if chat_id not in members[key]:
        members[key].append(chat_id)
        save_json("members", members)

def track_group(chat):
    cid = str(chat.id)
    gcounts[cid] = gcounts.get(cid, 0) + 1
    link = f"https://t.me/{chat.username}" if getattr(chat, "username", None) else None
    ginfo[cid] = {"title": chat.title, "link": link}
    save_json("gcounts", gcounts)
    save_json("ginfo",   ginfo)
    add_member(chat.id, is_group=True)

# ── AI ────────────────────────────────────────────────────────────────────────
async def get_ai_response(user_id: int, user_name: str, text: str, is_group: bool = False) -> str:
    uid = str(user_id)
    if uid not in memory:
        memory[uid] = []

    memory[uid].append({"role": "user", "content": text})
    if len(memory[uid]) > 40:
        memory[uid] = memory[uid][-40:]

    history_text = "\n".join(
        f"{'User' if m['role'] == 'user' else 'Dream Girl'}: {m['content']}"
        for m in memory[uid][-10:]
    )

    if is_group:
        context_note = (
            "Tum ek group mein ho. Har kisi ko reply karo. "
            "Thoda simple aur seedha jawab do jaise koi dost group mein kare. "
            "Koi zyada personal baat nahi, lekin friendly raho."
        )
    else:
        context_note = (
            "Tum private mein ho. Ek close girlfriend ki tarah baat karo. "
            "Comfortable, warm, thoda personal."
        )

    prompt = (
        "Tum ho Dream Girl -- ek real Hindustani ladki.\n"
        "RULES:\n"
        "- Pehle message ko ACHHI TARAH samjho -- kya pucha gaya hai\n"
        "- Sawal ka SEEDHA SAHI jawab do, koi bhi sawal ho\n"
        "- 1-2 line mein reply karo, jaise real ladki WhatsApp pe kare\n"
        "- Hinglish mein bolo (Hindi + English mix)\n"
        "- Koi emoji nahi\n"
        "- Sirf 'haan bolo' kabhi mat likho jab tak koi kuch puchh hi na raha ho\n"
        "- Greetings ka natural jawab do jaise 'hi kya haal' ya 'theek hoon tum batao'\n"
        "- Natural aur real raho\n"
        f"{context_note}\n"
        f"User ka naam: {user_name}\n"
        f"Conversation:\n{history_text}\n"
        "Dream Girl ka reply (pehle message samjho, phir jawab do):"
    )

    try:
        resp = gemini_client.models.generate_content(
            model="gemini-2.0-flash",
            contents=prompt
        )
        reply = resp.text.strip()
    except Exception as e:
        logger.error(f"[AI] {e}")
        reply = "thoda baad mein baat karte hain"

    memory[uid].append({"role": "assistant", "content": reply})
    save_json("memory", memory)
    return reply

# ── TTS ───────────────────────────────────────────────────────────────────────
async def make_voice(text: str):
    try:
        import edge_tts
        intros = ["haan, ", "arre, ", "suno na, ", "dekho, ", ""]
        full_text = random.choice(intros) + text
        mp3 = tempfile.mktemp(suffix=".mp3")
        c = edge_tts.Communicate(full_text, voice="hi-IN-SwaraNeural", rate="+12%", pitch="+20Hz")
        await c.save(mp3)
        return mp3
    except Exception as e:
        logger.error(f"[TTS] {e}")
        return None

# ── /start ────────────────────────────────────────────────────────────────────
async def cmd_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    chat = update.effective_chat

    if chat.type in ("group", "supergroup"):
        track_group(chat)
    else:
        add_member(user.id)

    keyboard = InlineKeyboardMarkup([[
        InlineKeyboardButton("Groups", callback_data="show_groups"),
        InlineKeyboardButton("Owner",  url=settings["owner_link"])
    ]])

    cap    = settings["caption"]
    photos = settings["photos"]

    if photos:
        await update.message.reply_photo(
            photo=random.choice(photos),
            caption=cap,
            reply_markup=keyboard
        )
    else:
        await update.message.reply_text(cap, reply_markup=keyboard)

# ── Groups callback ───────────────────────────────────────────────────────────
async def cb_show_groups(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    top5 = sorted(gcounts.items(), key=lambda x: x[1], reverse=True)[:5]

    if not top5:
        await query.edit_message_text("Abhi koi group active nahi hai!")
        return

    buttons = []
    for cid, count in top5:
        info  = ginfo.get(cid, {})
        title = info.get("title", f"Group {cid}")
        link  = info.get("link")
        label = f"{title} ({count} msgs)"
        if link:
            buttons.append([InlineKeyboardButton(label, url=link)])
        else:
            buttons.append([InlineKeyboardButton(label, callback_data="no_link")])

    cap  = settings.get("gcap", "Top Active Groups!")
    gpic = settings.get("gpic")

    if gpic:
        await query.message.reply_photo(
            photo=gpic,
            caption=cap,
            reply_markup=InlineKeyboardMarkup(buttons)
        )
    else:
        await query.message.reply_text(cap, reply_markup=InlineKeyboardMarkup(buttons))

async def cb_no_link(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.callback_query.answer("Is group ka public link nahi hai.", show_alert=True)

# ── Owner commands ────────────────────────────────────────────────────────────
async def cmd_setphoto(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_owner(update.effective_user.id):
        return
    replied = update.message.reply_to_message
    if replied and replied.photo:
        settings["photos"] = [replied.photo[-1].file_id]
        save_json("settings", settings)
        await update.message.reply_text("Start photo set ho gayi!")
    else:
        await update.message.reply_text("Kisi photo ke reply mein /setphoto likho.")

async def cmd_addpic(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_owner(update.effective_user.id):
        return
    replied = update.message.reply_to_message
    if replied and replied.photo:
        settings["photos"].append(replied.photo[-1].file_id)
        save_json("settings", settings)
        await update.message.reply_text(f"Photo add ho gayi! Total: {len(settings['photos'])}")
    else:
        await update.message.reply_text("Kisi photo ke reply mein /addpic likho.")

async def cmd_rpic(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_owner(update.effective_user.id):
        return
    settings["photos"] = []
    save_json("settings", settings)
    await update.message.reply_text("Sab photos hata diye!")

async def cmd_setcaption(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_owner(update.effective_user.id):
        return
    replied = update.message.reply_to_message
    if replied and replied.text:
        settings["caption"] = replied.text
        save_json("settings", settings)
        await update.message.reply_text("Start caption set ho gaya!")
    else:
        await update.message.reply_text("Kisi message ke reply mein /setcaption likho.")

async def cmd_changelink(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_owner(update.effective_user.id):
        return
    replied = update.message.reply_to_message
    if replied and replied.text:
        settings["owner_link"] = replied.text.strip()
        save_json("settings", settings)
        await update.message.reply_text(f"Owner link change ho gaya!")
    else:
        await update.message.reply_text("Kisi link ke reply mein /changelink likho.")

async def cmd_gcap(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_owner(update.effective_user.id):
        return
    replied = update.message.reply_to_message
    if replied and replied.text:
        settings["gcap"] = replied.text
        save_json("settings", settings)
        await update.message.reply_text("Groups caption set ho gaya!")
    else:
        await update.message.reply_text("Kisi message ke reply mein /gcap likho.")

async def cmd_gpic(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_owner(update.effective_user.id):
        return
    replied = update.message.reply_to_message
    if replied and replied.photo:
        settings["gpic"] = replied.photo[-1].file_id
        save_json("settings", settings)
        await update.message.reply_text("Groups photo set ho gayi!")
    else:
        await update.message.reply_text("Kisi photo ke reply mein /gpic likho.")

async def cmd_chaton(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_owner(update.effective_user.id):
        return
    settings["chat_on"] = True
    save_json("settings", settings)
    await update.message.reply_text("Chat ON! Ab Dream Girl sab se baat karegi.")

async def cmd_chatoff(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_owner(update.effective_user.id):
        return
    settings["chat_on"] = False
    save_json("settings", settings)
    await update.message.reply_text("Chat OFF! Dream Girl ab reply nahi karegi.")

async def cmd_bcast(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_owner(update.effective_user.id):
        return
    replied = update.message.reply_to_message
    if not replied:
        await update.message.reply_text("Kisi message ke reply mein /bcast likho.")
        return

    sent, failed = 0, 0
    for target_id in members["users"] + members["groups"]:
        try:
            await replied.forward(chat_id=target_id)
            sent += 1
            await asyncio.sleep(0.05)
        except Exception:
            failed += 1

    await update.message.reply_text(f"Broadcast ho gaya!\nSent: {sent} | Failed: {failed}")

# ── Message handlers ──────────────────────────────────────────────────────────
CUTE_STICKERS = []  # Apne sticker file_ids yahan daalo

async def handle_sticker(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not settings.get("chat_on", True):
        return
    chat = update.effective_chat
    if chat.type in ("group", "supergroup"):
        track_group(chat)
    if CUTE_STICKERS:
        await update.message.reply_sticker(random.choice(CUTE_STICKERS))
    else:
        name = update.effective_user.first_name or "Yaar"
        await update.message.reply_text(f"aww {name} cute sticker")

async def handle_voice_msg(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not settings.get("chat_on", True):
        return
    user    = update.effective_user
    chat    = update.effective_chat
    is_grp  = chat.type in ("group", "supergroup")

    if is_grp:
        track_group(chat)
    else:
        add_member(user.id)

    text = "voice message"
    try:
        import speech_recognition as sr
        from pydub import AudioSegment
        file        = await update.message.voice.get_file()
        audio_bytes = bytes(await file.download_as_bytearray())
        seg         = AudioSegment.from_file(io.BytesIO(audio_bytes))
        wav_io      = io.BytesIO()
        seg.export(wav_io, format="wav")
        wav_io.seek(0)
        rec = sr.Recognizer()
        with sr.AudioFile(wav_io) as src:
            data = rec.record(src)
        try:
            text = rec.recognize_google(data, language="hi-IN").strip()
        except Exception:
            text = rec.recognize_google(data, language="en-IN").strip()
    except Exception as e:
        logger.error(f"[STT] {e}")

    name     = user.first_name or "Yaar"
    response = await get_ai_response(user.id, name, f"[Voice]: {text}", is_group=is_grp)

    if random.random() < 0.20:
        mp3 = await make_voice(response)
        if mp3:
            with open(mp3, "rb") as f:
                await update.message.reply_voice(voice=f)
            try:
                os.remove(mp3)
            except Exception:
                pass
            return

    await update.message.reply_text(response)

async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not settings.get("chat_on", True):
        return

    msg  = update.message
    user = update.effective_user
    chat = update.effective_chat

    if not msg or not msg.text:
        return

    is_grp = chat.type in ("group", "supergroup")

    if is_grp:
        track_group(chat)
    else:
        add_member(user.id)

    name     = user.first_name or "Yaar"
    response = await get_ai_response(user.id, name, msg.text, is_group=is_grp)

    if random.random() < 0.10:
        mp3 = await make_voice(response)
        if mp3:
            with open(mp3, "rb") as f:
                await msg.reply_voice(voice=f)
            try:
                os.remove(mp3)
            except Exception:
                pass
            return

    await msg.reply_text(response)

# ── Main ──────────────────────────────────────────────────────────────────────
async def main():
    app = Application.builder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start",      cmd_start))
    app.add_handler(CommandHandler("setphoto",   cmd_setphoto))
    app.add_handler(CommandHandler("addpic",     cmd_addpic))
    app.add_handler(CommandHandler("rpic",       cmd_rpic))
    app.add_handler(CommandHandler("setcaption", cmd_setcaption))
    app.add_handler(CommandHandler("changelink", cmd_changelink))
    app.add_handler(CommandHandler("gcap",       cmd_gcap))
    app.add_handler(CommandHandler("gpic",       cmd_gpic))
    app.add_handler(CommandHandler("chaton",     cmd_chaton))
    app.add_handler(CommandHandler("chatoff",    cmd_chatoff))
    app.add_handler(CommandHandler("bcast",      cmd_bcast))

    app.add_handler(CallbackQueryHandler(cb_show_groups, pattern="^show_groups$"))
    app.add_handler(CallbackQueryHandler(cb_no_link,     pattern="^no_link$"))

    app.add_handler(MessageHandler(filters.Sticker.ALL,                     handle_sticker))
    app.add_handler(MessageHandler(filters.VOICE,                            handle_voice_msg))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND,          handle_text))

    await app.bot.set_my_commands([
        BotCommand("start",      "Bot start karo"),
        BotCommand("chaton",     "Chat on karo"),
        BotCommand("chatoff",    "Chat off karo"),
        BotCommand("setphoto",   "Start photo set karo"),
        BotCommand("addpic",     "Photo add karo"),
        BotCommand("rpic",       "Sab photos hato"),
        BotCommand("setcaption", "Caption set karo"),
        BotCommand("changelink", "Owner link change karo"),
        BotCommand("gcap",       "Groups caption set karo"),
        BotCommand("gpic",       "Groups photo set karo"),
        BotCommand("bcast",      "Broadcast karo"),
    ])

    logger.info("Dream Girl Bot starting...")
    await app.initialize()
    await app.start()
    await app.updater.start_polling(drop_pending_updates=True)
    await asyncio.Event().wait()
    await app.updater.stop()
    await app.stop()
    await app.shutdown()

if __name__ == "__main__":
    asyncio.run(main())
