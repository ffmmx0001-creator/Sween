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

DATA_DIR = "data"
os.makedirs(DATA_DIR, exist_ok=True)

def load_json(name, default):
    path = f"{DATA_DIR}/{name}.json"
    if os.path.exists(path):
        with open(path) as f:
            return json.load(f)
    return default

def save_json(name, data):
    with open(f"{DATA_DIR}/{name}.json", "w") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

settings = load_json("settings", {
    "caption": "Hiii! Main hoon Dream Girl\nTumhari pyaari AI girlfriend!",
    "photos": [],
    "owner_link": "https://t.me/owner",
    "gcap": "Top Groups jahan Dream Girl active hai!",
    "gpic": None,
    "chat_on": True
})
memory  = load_json("memory", {})
gcounts = load_json("gcounts", {})
ginfo   = load_json("ginfo", {})
members = load_json("members", {"users": [], "groups": []})


def is_owner(user_id):
    return user_id == OWNER_ID


def add_member(chat_id, is_group=False):
    key = "groups" if is_group else "users"
    if chat_id not in members[key]:
        members[key].append(chat_id)
        save_json("members", members)


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
            "Tum abhi ek group mein ho. Thoda sharminda aur seedha jawab do, "
            "jaise koi ladki bahar logon ke saamne baat kare. "
            "Zyada personal mat ho, lekin friendly raho."
        )
    else:
        context_note = (
            "Tum abhi private mein ho, akele uske saath. "
            "Jaise ghar par baat kar rahi ho -- comfortable, close, thoda naughty bhi kabhi kabhi. "
            "Seedhi baat karo, dil ki."
        )

    prompt = (
        "Tum ho Dream Girl -- ek real cute pyaari girlfriend.\n"
        "RULES:\n"
        "- Sirf 1-2 line mein reply karo, jaise real ladki WhatsApp pe kare\n"
        "- Hinglish use karo (Hindi + English mix)\n"
        "- Koi emoji use mat karo\n"
        "- Natural raho -- kabhi flirty, kabhi shy, kabhi caring\n"
        "- Koi lecture nahi, koi long paragraph nahi\n"
        f"{context_note}\n"
        f"User ka naam: {user_name}\n"
        f"Conversation:\n{history_text}\n"
        "Dream Girl ka chhota sa reply:"
    )

    try:
        resp = gemini_client.models.generate_content(
            model="gemini-2.0-flash",
            contents=prompt
        )
        reply = resp.text.strip()
    except Exception as e:
        logger.error(f"[AI] {e}")
        reply = "haan bolo"

    memory[uid].append({"role": "assistant", "content": reply})
    save_json("memory", memory)
    return reply


async def make_voice(text: str) -> str | None:
    try:
        import edge_tts
        intros = ["haan, ", "arre, ", "suno na, ", "dekho, ", ""]
        full_text = random.choice(intros) + text
        mp3 = tempfile.mktemp(suffix=".mp3")
        c = edge_tts.Communicate(
            full_text,
            voice="hi-IN-SwaraNeural",
            rate="+12%",
            pitch="+20Hz"
        )
        await c.save(mp3)
        return mp3
    except Exception as e:
        logger.error(f"[TTS] {e}")
        return None


async def cmd_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    chat = update.effective_chat

    if chat.type in ("group", "supergroup"):
        add_member(chat.id, is_group=True)
        if chat.username:
            ginfo[str(chat.id)] = {"title": chat.title, "link": f"https://t.me/{chat.username}"}
        else:
            ginfo[str(chat.id)] = {"title": chat.title, "link": None}
        save_json("ginfo", ginfo)
    else:
        add_member(user.id)

    keyboard = InlineKeyboardMarkup([
        [
            InlineKeyboardButton("Groups", callback_data="show_groups"),
            InlineKeyboardButton("Owner", url=settings["owner_link"])
        ]
    ])

    cap = settings["caption"]
    photos = settings["photos"]

    if photos:
        photo = random.choice(photos)
        await update.message.reply_photo(photo=photo, caption=cap, reply_markup=keyboard)
    else:
        await update.message.reply_text(cap, reply_markup=keyboard)


async def cb_show_groups(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    sorted_groups = sorted(gcounts.items(), key=lambda x: x[1], reverse=True)[:5]

    if not sorted_groups:
        await query.edit_message_text("Abhi koi group active nahi hai!")
        return

    buttons = []
    for cid, count in sorted_groups:
        info = ginfo.get(cid, {})
        title = info.get("title", f"Group {cid}")
        link = info.get("link")
        if link:
            buttons.append([InlineKeyboardButton(f"{title} ({count} msgs)", url=link)])
        else:
            buttons.append([InlineKeyboardButton(f"{title} ({count} msgs)", callback_data="no_link")])

    cap = settings.get("gcap", "Top Active Groups!")
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
    await update.callback_query.answer("Is group ka public link available nahi hai.", show_alert=True)


async def cmd_setphoto(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_owner(update.effective_user.id):
        return
    msg = update.message
    replied = msg.reply_to_message
    if replied and replied.photo:
        file_id = replied.photo[-1].file_id
        settings["photos"] = [file_id]
        save_json("settings", settings)
        await msg.reply_text("Start message ki photo set ho gayi!")
    else:
        await msg.reply_text("Kisi photo ke reply mein /setphoto likho.")


async def cmd_addpic(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_owner(update.effective_user.id):
        return
    msg = update.message
    replied = msg.reply_to_message
    if replied and replied.photo:
        file_id = replied.photo[-1].file_id
        settings["photos"].append(file_id)
        save_json("settings", settings)
        await msg.reply_text(f"Photo add ho gayi! Total: {len(settings['photos'])} photos.")
    else:
        await msg.reply_text("Kisi photo ke reply mein /addpic likho.")


async def cmd_rpic(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_owner(update.effective_user.id):
        return
    settings["photos"] = []
    save_json("settings", settings)
    await update.message.reply_text("Sab photos hata diye!")


async def cmd_setcaption(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_owner(update.effective_user.id):
        return
    msg = update.message
    replied = msg.reply_to_message
    if replied and replied.text:
        settings["caption"] = replied.text
        save_json("settings", settings)
        await msg.reply_text("Start message caption set ho gaya!")
    else:
        await msg.reply_text("Kisi message ke reply mein /setcaption likho.")


async def cmd_changelink(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_owner(update.effective_user.id):
        return
    msg = update.message
    replied = msg.reply_to_message
    if replied and replied.text:
        link = replied.text.strip()
        settings["owner_link"] = link
        save_json("settings", settings)
        await msg.reply_text(f"Owner link change ho gaya: {link}")
    else:
        await msg.reply_text("Kisi link ke reply mein /changelink likho.")


async def cmd_gcap(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_owner(update.effective_user.id):
        return
    msg = update.message
    replied = msg.reply_to_message
    if replied and replied.text:
        settings["gcap"] = replied.text
        save_json("settings", settings)
        await msg.reply_text("Groups page caption set ho gaya!")
    else:
        await msg.reply_text("Kisi message ke reply mein /gcap likho.")


async def cmd_gpic(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_owner(update.effective_user.id):
        return
    msg = update.message
    replied = msg.reply_to_message
    if replied and replied.photo:
        settings["gpic"] = replied.photo[-1].file_id
        save_json("settings", settings)
        await msg.reply_text("Groups page photo set ho gayi!")
    else:
        await msg.reply_text("Kisi photo ke reply mein /gpic likho.")


async def cmd_chat_on(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_owner(update.effective_user.id):
        return
    settings["chat_on"] = True
    save_json("settings", settings)
    await update.message.reply_text("Chat mode ON! Ab Dream Girl sab se baat karegi.")


async def cmd_chat_off(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_owner(update.effective_user.id):
        return
    settings["chat_on"] = False
    save_json("settings", settings)
    await update.message.reply_text("Chat mode OFF! Dream Girl ab reply nahi karegi.")


async def cmd_bcast(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_owner(update.effective_user.id):
        return
    msg = update.message
    replied = msg.reply_to_message
    if not replied:
        await msg.reply_text("Kisi message ke reply mein /bcast likho.")
        return

    sent, failed = 0, 0
    all_targets = members["users"] + members["groups"]

    for target_id in all_targets:
        try:
            await replied.forward(chat_id=target_id)
            sent += 1
            await asyncio.sleep(0.05)
        except Exception:
            failed += 1

    await msg.reply_text(f"Broadcast ho gaya!\nSent: {sent} | Failed: {failed}")


CUTE_STICKERS = []  # Apne sticker file_ids yahan daalo


async def handle_sticker(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not settings.get("chat_on", True):
        return
    chat = update.effective_chat
    if chat.type in ("group", "supergroup"):
        cid = str(chat.id)
        gcounts[cid] = gcounts.get(cid, 0) + 1
        save_json("gcounts", gcounts)
    if CUTE_STICKERS:
        sticker = random.choice(CUTE_STICKERS)
        await update.message.reply_sticker(sticker)
    else:
        await update.message.reply_text("aww cute")


async def handle_voice_msg(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not settings.get("chat_on", True):
        return
    user = update.effective_user
    chat = update.effective_chat
    is_group = chat.type in ("group", "supergroup")

    if is_group:
        cid = str(chat.id)
        gcounts[cid] = gcounts.get(cid, 0) + 1
        save_json("gcounts", gcounts)
        add_member(chat.id, is_group=True)
    else:
        add_member(user.id)

    try:
        import speech_recognition as sr
        from pydub import AudioSegment
        file = await update.message.voice.get_file()
        audio_bytes = await file.download_as_bytearray()
        seg = AudioSegment.from_file(io.BytesIO(bytes(audio_bytes)))
        wav_io = io.BytesIO()
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
        text = "voice message"

    name = user.first_name if user else "Yaar"
    response = await get_ai_response(user.id, name, f"[Voice]: {text}", is_group=is_group)

    if random.random() < 0.20:
        mp3 = await make_voice(response)
        if mp3:
            await update.message.reply_voice(voice=open(mp3, "rb"))
            try:
                os.remove(mp3)
            except Exception:
                pass
            return

    await update.message.reply_text(response)


async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not settings.get("chat_on", True):
        return

    user = update.effective_user
    chat = update.effective_chat
    msg = update.message
    if not msg or not msg.text:
        return

    is_group = chat.type in ("group", "supergroup")

    if is_group:
        cid = str(chat.id)
        gcounts[cid] = gcounts.get(cid, 0) + 1
        save_json("gcounts", gcounts)
        add_member(chat.id, is_group=True)
        if chat.username:
            ginfo[cid] = {"title": chat.title, "link": f"https://t.me/{chat.username}"}
        else:
            ginfo[cid] = {"title": chat.title, "link": None}
        save_json("ginfo", ginfo)

        bot_username = context.bot.username
        is_mentioned = f"@{bot_username}".lower() in msg.text.lower()
        is_reply_to_bot = (
            msg.reply_to_message and
            msg.reply_to_message.from_user and
            msg.reply_to_message.from_user.id == context.bot.id
        )
        if not is_mentioned and not is_reply_to_bot:
            return
    else:
        add_member(user.id)

    name = user.first_name if user else "Yaar"
    response = await get_ai_response(user.id, name, msg.text, is_group=is_group)

    if random.random() < 0.10:
        mp3 = await make_voice(response)
        if mp3:
            await msg.reply_voice(voice=open(mp3, "rb"))
            try:
                os.remove(mp3)
            except Exception:
                pass
            return

    await msg.reply_text(response)


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
    app.add_handler(CommandHandler("chaton",     cmd_chat_on))
    app.add_handler(CommandHandler("chatoff",    cmd_chat_off))
    app.add_handler(CommandHandler("bcast",      cmd_bcast))

    app.add_handler(CallbackQueryHandler(cb_show_groups, pattern="show_groups"))
    app.add_handler(CallbackQueryHandler(cb_no_link,     pattern="no_link"))

    app.add_handler(MessageHandler(filters.Sticker.ALL,                    handle_sticker))
    app.add_handler(MessageHandler(filters.VOICE,                           handle_voice_msg))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND,         handle_text))

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

