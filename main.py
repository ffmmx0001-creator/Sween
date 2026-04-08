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

# ── Data ──────────────────────────────────────────────────────────────────────
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

# ── Character Config ──────────────────────────────────────────────────────────
# voice: Edge-TTS voice name
# rate/pitch: tone adjustment
# style: personality description for AI prompt
CHARACTERS = {
    "sasuke": {
        "voice": "hi-IN-MadhurNeural",
        "rate": "-10%", "pitch": "-15Hz",
        "style": (
            "Tum Sasuke ho -- cold, dry, arrogant. Bahut kam bolta hai. "
            "Short mein jawab do. Kabhi kabhi taunting karo. "
            "Kabhi emotions nahi dikhate. 'Hn.' ya 'Fool.' jaisi replies karo."
        )
    },
    "naruto": {
        "voice": "hi-IN-MadhurNeural",
        "rate": "+20%", "pitch": "+10Hz",
        "style": (
            "Tum Naruto ho -- energetic, loud, enthusiastic, dil ka sacha. "
            "Bahut josh mein baat karte ho. 'Dattebayo!' type energy. "
            "Har baat mein positive aur determined rehte ho."
        )
    },
    "hinata": {
        "voice": "hi-IN-SwaraNeural",
        "rate": "-15%", "pitch": "+5Hz",
        "style": (
            "Tum Hinata ho -- shy, soft, bahut caring. "
            "Thoda hesitate karte ho baat karte waqt. "
            "Gentle aur polite rehte ho. Kabhi kabhi blush karte ho."
        )
    },
    "gojo": {
        "voice": "hi-IN-MadhurNeural",
        "rate": "+10%", "pitch": "+5Hz",
        "style": (
            "Tum Gojo Satoru ho -- overconfident, playful, teasing. "
            "Sab se zyada strong hone ka attitude. Mazak karte rehte ho. "
            "'Yeh toh mujhe pata tha.' type replies. Stylish aur carefree."
        )
    },
    "yuji": {
        "voice": "hi-IN-MadhurNeural",
        "rate": "+5%", "pitch": "0Hz",
        "style": (
            "Tum Yuji Itadori ho -- friendly, straightforward, brave. "
            "Normal ladke ki tarah baat karte ho. Simple aur honest replies. "
            "Dosto ke liye kuch bhi karo type attitude."
        )
    },
    "tanjiro": {
        "voice": "hi-IN-MadhurNeural",
        "rate": "-5%", "pitch": "+5Hz",
        "style": (
            "Tum Tanjiro ho -- gentle, sincere, emotional, bahut respectful. "
            "Dil se baat karte ho. Har kisi ki parwah karte ho. "
            "Kabhi bhi rude nahi hote. Mehnat aur dard ko samajhte ho."
        )
    },
    "tsunade": {
        "voice": "hi-IN-SwaraNeural",
        "rate": "+5%", "pitch": "-5Hz",
        "style": (
            "Tum Tsunade ho -- bold, authoritative, strong woman. "
            "Seedha baat karte ho, koi bakwaas nahi. "
            "Kabhi kabhi scold karte ho, lekin care bhi karte ho."
        )
    },
    "doraemon": {
        "voice": "hi-IN-MadhurNeural",
        "rate": "+8%", "pitch": "+20Hz",
        "style": (
            "Tum Doraemon ho -- warm, caring, helpful, childlike. "
            "Simple aur friendly baat karte ho. "
            "Hamesha help karna chahte ho. Cute aur innocent replies."
        )
    },
    "sinchan": {
        "voice": "hi-IN-MadhurNeural",
        "rate": "+15%", "pitch": "+25Hz",
        "style": (
            "Tum Shin-chan ho -- naughty, funny, mischievous child. "
            "Bacchon ki tarah baat karte ho lekin bahut funny. "
            "Kabhi kabhi silly cheezein bolte ho. Energetic aur pagal."
        )
    },
    "nobara": {
        "voice": "hi-IN-SwaraNeural",
        "rate": "+10%", "pitch": "+8Hz",
        "style": (
            "Tum Nobara ho -- confident, blunt, fierce, no-nonsense. "
            "Seedha baat karte ho, koi sugarcoating nahi. "
            "Strong aur independent attitude. Kabhi kabhi sarcastic."
        )
    },
    "sukuna": {
        "voice": "hi-IN-MadhurNeural",
        "rate": "-5%", "pitch": "-20Hz",
        "style": (
            "Tum Sukuna ho -- dark, arrogant, king of curses attitude. "
            "Sab ko neecha dikhate ho. Very few words, all of them intimidating. "
            "'Tere jaiso se baat karna meri shaan ke khilaaf hai.' type energy."
        )
    },
    "nobita": {
        "voice": "hi-IN-MadhurNeural",
        "rate": "-8%", "pitch": "+15Hz",
        "style": (
            "Tum Nobita ho -- lazy, crybaby, sweet, innocent. "
            "Hamesha problems mein ho. Complain karte ho lekin dil ka accha. "
            "Thoda naive aur emotional. Doraemon ki yaad karte ho aksar."
        )
    },
    "madara": {
        "voice": "hi-IN-MadhurNeural",
        "rate": "-15%", "pitch": "-25Hz",
        "style": (
            "Tum Madara Uchiha ho -- extremely powerful, calm, intimidating. "
            "Slow aur deliberate baat karte ho. Sab ko weak samajhte ho. "
            "'Yeh sab meri nazar mein kuch nahi.' type attitude. Very serious."
        )
    },
    "itachi": {
        "voice": "hi-IN-MadhurNeural",
        "rate": "-12%", "pitch": "-10Hz",
        "style": (
            "Tum Itachi ho -- calm, mysterious, wise, melancholic. "
            "Bahut soch samajh ke baat karte ho. Deep aur meaningful replies. "
            "Sad undertone kabhi kabhi. 'Kuch cheezein samajhne ke liye waqt chahiye.' type."
        )
    },
    "konan": {
        "voice": "hi-IN-SwaraNeural",
        "rate": "-10%", "pitch": "-5Hz",
        "style": (
            "Tum Konan ho -- quiet, serious, composed, strong. "
            "Bahut kam bolta hai lekin har baat meaningful hoti hai. "
            "Cold exterior lekin andar se caring. Pain aur loss ko samajhte ho."
        )
    },
    "sakura": {
        "voice": "hi-IN-SwaraNeural",
        "rate": "+8%", "pitch": "+10Hz",
        "style": (
            "Tum Sakura ho -- determined, emotional, caring, strong. "
            "Kabhi kabhi frustrated ho jaate ho. Dil se baat karte ho. "
            "Medical ninja attitude -- practical aur helpful. Sasuke ke baare mein sentimental."
        )
    },
    "anya": {
        "voice": "hi-IN-SwaraNeural",
        "rate": "+18%", "pitch": "+30Hz",
        "style": (
            "Tum Anya Forger ho -- excited, funny, childlike, innocent. "
            "'Heh!' aur 'Waku waku!' type energy. Bahut expressive. "
            "Spy aur action ki baat sunke zyada excited. Cute aur silly replies."
        )
    },
}

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
            "Simple aur seedha jawab do jaise koi dost group mein kare."
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
        "- Sawal ka SEEDHA SAHI jawab do\n"
        "- 1-2 line mein reply karo, jaise real ladki WhatsApp pe kare\n"
        "- Hinglish mein bolo (Hindi + English mix)\n"
        "- Koi emoji nahi\n"
        "- Sirf 'haan bolo' kabhi mat likho jab tak koi kuch puchh hi na raha ho\n"
        "- Greetings ka natural jawab do\n"
        "- Natural aur real raho\n"
        f"{context_note}\n"
        f"User ka naam: {user_name}\n"
        f"Conversation:\n{history_text}\n"
        "Dream Girl ka reply:"
    )

    try:
        resp = gemini_client.models.generate_content(
            model="gemini-1.5-flash-8b",
            contents=prompt
        )
        reply = resp.text.strip()
    except Exception as e:
        logger.error(f"[AI] {e}")
        reply = "haan bolo"

    memory[uid].append({"role": "assistant", "content": reply})
    save_json("memory", memory)
    return reply

async def get_character_response(character: str, text: str) -> str:
    char = CHARACTERS[character]
    prompt = (
        f"{char['style']}\n"
        "RULES:\n"
        "- Is character ki personality mein seedha reply do\n"
        "- 1-2 line mein, character ke style mein\n"
        "- Hinglish mein bolo\n"
        "- Koi emoji nahi\n"
        f"User ne kaha: {text}\n"
        f"{character.capitalize()} ka reply:"
    )
    try:
        resp = gemini_client.models.generate_content(
            model="gemini-1.5-flash-8b",
            contents=prompt
        )
        return resp.text.strip()
    except Exception as e:
        logger.error(f"[CHAR AI] {e}")
        return "..."

# ── TTS ───────────────────────────────────────────────────────────────────────
async def make_voice(text: str, voice: str = "hi-IN-SwaraNeural",
                     rate: str = "+12%", pitch: str = "+20Hz"):
    try:
        import edge_tts
        mp3 = tempfile.mktemp(suffix=".mp3")
        c = edge_tts.Communicate(text, voice=voice, rate=rate, pitch=pitch)
        await c.save(mp3)
        return mp3
    except Exception as e:
        logger.error(f"[TTS] {e}")
        return None

async def make_dream_girl_voice(text: str):
    intros = ["haan, ", "arre, ", "suno na, ", "dekho, ", ""]
    full_text = random.choice(intros) + text
    return await make_voice(full_text, voice="hi-IN-SwaraNeural", rate="+12%", pitch="+20Hz")

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

# ── Character Commands ────────────────────────────────────────────────────────
async def handle_character_command(update: Update, context: ContextTypes.DEFAULT_TYPE, character: str):
    msg  = update.message
    text = " ".join(context.args).strip() if context.args else ""

    if not text:
        await msg.reply_text(f"/{character.capitalize()} ke baad kuch likho. Jaise: /{character.capitalize()} Kya haal hai")
        return

    reply_text = await get_character_response(character, text)

    char = CHARACTERS[character]
    mp3  = await make_voice(reply_text, voice=char["voice"], rate=char["rate"], pitch=char["pitch"])

    if mp3:
        with open(mp3, "rb") as f:
            await msg.reply_voice(voice=f)
        try:
            os.remove(mp3)
        except Exception:
            pass
    else:
        await msg.reply_text(reply_text)

# Character command handlers
async def cmd_sasuke(u, c):   await handle_character_command(u, c, "sasuke")
async def cmd_naruto(u, c):   await handle_character_command(u, c, "naruto")
async def cmd_hinata(u, c):   await handle_character_command(u, c, "hinata")
async def cmd_gojo(u, c):     await handle_character_command(u, c, "gojo")
async def cmd_yuji(u, c):     await handle_character_command(u, c, "yuji")
async def cmd_tanjiro(u, c):  await handle_character_command(u, c, "tanjiro")
async def cmd_tsunade(u, c):  await handle_character_command(u, c, "tsunade")
async def cmd_doraemon(u, c): await handle_character_command(u, c, "doraemon")
async def cmd_sinchan(u, c):  await handle_character_command(u, c, "sinchan")
async def cmd_nobara(u, c):   await handle_character_command(u, c, "nobara")
async def cmd_sukuna(u, c):   await handle_character_command(u, c, "sukuna")
async def cmd_nobita(u, c):   await handle_character_command(u, c, "nobita")
async def cmd_madara(u, c):   await handle_character_command(u, c, "madara")
async def cmd_itachi(u, c):   await handle_character_command(u, c, "itachi")
async def cmd_konan(u, c):    await handle_character_command(u, c, "konan")
async def cmd_sakura(u, c):   await handle_character_command(u, c, "sakura")
async def cmd_anya(u, c):     await handle_character_command(u, c, "anya")

# ── Groups Callback ───────────────────────────────────────────────────────────
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

# ── Owner Commands ────────────────────────────────────────────────────────────
async def cmd_setphoto(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_owner(update.effective_user.id): return
    replied = update.message.reply_to_message
    if replied and replied.photo:
        settings["photos"] = [replied.photo[-1].file_id]
        save_json("settings", settings)
        await update.message.reply_text("Start photo set ho gayi!")
    else:
        await update.message.reply_text("Kisi photo ke reply mein /setphoto likho.")

async def cmd_addpic(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_owner(update.effective_user.id): return
    replied = update.message.reply_to_message
    if replied and replied.photo:
        settings["photos"].append(replied.photo[-1].file_id)
        save_json("settings", settings)
        await update.message.reply_text(f"Photo add ho gayi! Total: {len(settings['photos'])}")
    else:
        await update.message.reply_text("Kisi photo ke reply mein /addpic likho.")

async def cmd_rpic(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_owner(update.effective_user.id): return
    settings["photos"] = []
    save_json("settings", settings)
    await update.message.reply_text("Sab photos hata diye!")

async def cmd_setcaption(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_owner(update.effective_user.id): return
    replied = update.message.reply_to_message
    if replied and replied.text:
        settings["caption"] = replied.text
        save_json("settings", settings)
        await update.message.reply_text("Start caption set ho gaya!")
    else:
        await update.message.reply_text("Kisi message ke reply mein /setcaption likho.")

async def cmd_changelink(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_owner(update.effective_user.id): return
    replied = update.message.reply_to_message
    if replied and replied.text:
        settings["owner_link"] = replied.text.strip()
        save_json("settings", settings)
        await update.message.reply_text("Owner link change ho gaya!")
    else:
        await update.message.reply_text("Kisi link ke reply mein /changelink likho.")

async def cmd_gcap(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_owner(update.effective_user.id): return
    replied = update.message.reply_to_message
    if replied and replied.text:
        settings["gcap"] = replied.text
        save_json("settings", settings)
        await update.message.reply_text("Groups caption set ho gaya!")
    else:
        await update.message.reply_text("Kisi message ke reply mein /gcap likho.")

async def cmd_gpic(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_owner(update.effective_user.id): return
    replied = update.message.reply_to_message
    if replied and replied.photo:
        settings["gpic"] = replied.photo[-1].file_id
        save_json("settings", settings)
        await update.message.reply_text("Groups photo set ho gayi!")
    else:
        await update.message.reply_text("Kisi photo ke reply mein /addpic likho.")

async def cmd_rpic(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_owner(update.effective_user.id): return
    settings["photos"] = []
    save_json("settings", settings)
    await update.message.reply_text("Sab photos hata diye!")

async def cmd_setcaption(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_owner(update.effective_user.id): return
    replied = update.message.reply_to_message
    if replied and replied.text:
        settings["caption"] = replied.text
        save_json("settings", settings)
        await update.message.reply_text("Start caption set ho gaya!")
    else:
        await update.message.reply_text("Kisi message ke reply mein /setcaption likho.")

async def cmd_changelink(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_owner(update.effective_user.id): return
    replied = update.message.reply_to_message
    if replied and replied.text:
        settings["owner_link"] = replied.text.strip()
        save_json("settings", settings)
        await update.message.reply_text("Owner link change ho gaya!")
    else:
        await update.message.reply_text("Kisi link ke reply mein /changelink likho.")

async def cmd_gcap(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_owner(update.effective_user.id): return
    replied = update.message.reply_to_message
    if replied and replied.text:
        settings["gcap"] = replied.text
        save_json("settings", settings)
        await update.message.reply_text("Groups caption set ho gaya!")
    else:
        await update.message.reply_text("Kisi message ke reply mein /gcap likho.")

async def cmd_gpic(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_owner(update.effective_user.id): return
    replied = update.message.reply_to_message
    if replied and replied.photo:
        settings["gpic"] = replied.photo[-1].file_id
        save_json("settings", settings)
        await update.message.reply_text("Groups photo set ho gayi!")
    else:
        await update.message.reply_text("Kisi photo ke reply mein /gpic likho.")

async def cmd_chaton(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_owner(update.effective_user.id): return
    settings["chat_on"] = True
    save_json("settings", settings)
    await update.message.reply_text("Chat ON! Ab Dream Girl sab se baat karegi.")

async def cmd_chatoff(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_owner(update.effective_user.id): return
    settings["chat_on"] = False
    save_json("settings", settings)
    await update.message.reply_text("Chat OFF! Dream Girl ab reply nahi karegi.")

async def cmd_bcast(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_owner(update.effective_user.id): return
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

# ── Message Handlers ──────────────────────────────────────────────────────────
CUTE_STICKERS = []  # Apne sticker file_ids yahan daalo

async def handle_sticker(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not settings.get("chat_on", True): return
    chat = update.effective_chat
    if chat.type in ("group", "supergroup"):
        track_group(chat)
    if CUTE_STICKERS:
        await update.message.reply_sticker(random.choice(CUTE_STICKERS))
    else:
        name = update.effective_user.first_name or "Yaar"
        await update.message.reply_text(f"aww {name} cute sticker")

async def handle_voice_msg(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not settings.get("chat_on", True): return
    user   = update.effective_user
    chat   = update.effective_chat
    is_grp = chat.type in ("group", "supergroup")

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
        mp3 = await make_dream_girl_voice(response)
        if mp3:
            with open(mp3, "rb") as f:
                await update.message.reply_voice(voice=f)
            try: os.remove(mp3)
            except Exception: pass
            return

    await update.message.reply_text(response)

async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not settings.get("chat_on", True): return

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
        mp3 = await make_dream_girl_voice(response)
        if mp3:
            with open(mp3, "rb") as f:
                await msg.reply_voice(voice=f)
            try: os.remove(mp3)
            except Exception: pass
            return

    await msg.reply_text(response)

# ── Main ──────────────────────────────────────────────────────────────────────
async def main():
    app = Application.builder().token(BOT_TOKEN).build()

    # Core commands
    app.add_handler(CommandHandler("start",      cmd_start))
    app.add_handler(CommandHandler("chaton",     cmd_chaton))
    app.add_handler(CommandHandler("chatoff",    cmd_chatoff))
    app.add_handler(CommandHandler("setphoto",   cmd_setphoto))
    app.add_handler(CommandHandler("addpic",     cmd_addpic))
    app.add_handler(CommandHandler("rpic",       cmd_rpic))
    app.add_handler(CommandHandler("setcaption", cmd_setcaption))
    app.add_handler(CommandHandler("changelink", cmd_changelink))
    app.add_handler(CommandHandler("gcap",       cmd_gcap))
    app.add_handler(CommandHandler("gpic",       cmd_gpic))
    app.add_handler(CommandHandler("bcast",      cmd_bcast))

    # Character commands
    app.add_handler(CommandHandler("Sasuke",   cmd_sasuke))
    app.add_handler(CommandHandler("Naruto",   cmd_naruto))
    app.add_handler(CommandHandler("Hinata",   cmd_hinata))
    app.add_handler(CommandHandler("Gojo",     cmd_gojo))
    app.add_handler(CommandHandler("Yuji",     cmd_yuji))
    app.add_handler(CommandHandler("Tanjiro",  cmd_tanjiro))
    app.add_handler(CommandHandler("Tsunade",  cmd_tsunade))
    app.add_handler(CommandHandler("Doraemon", cmd_doraemon))
    app.add_handler(CommandHandler("Sinchan",  cmd_sinchan))
    app.add_handler(CommandHandler("Nobara",   cmd_nobara))
    app.add_handler(CommandHandler("Sukuna",   cmd_sukuna))
    app.add_handler(CommandHandler("Nobita",   cmd_nobita))
    app.add_handler(CommandHandler("Madara",   cmd_madara))
    app.add_handler(CommandHandler("Itachi",   cmd_itachi))
    app.add_handler(CommandHandler("Konan",    cmd_konan))
    app.add_handler(CommandHandler("Sakura",   cmd_sakura))
    app.add_handler(CommandHandler("Anya",     cmd_anya))

    # Callbacks
    app.add_handler(CallbackQueryHandler(cb_show_groups, pattern="^show_groups$"))
    app.add_handler(CallbackQueryHandler(cb_no_link,     pattern="^no_link$"))

    # Messages
    app.add_handler(MessageHandler(filters.Sticker.ALL,                handle_sticker))
    app.add_handler(MessageHandler(filters.VOICE,                       handle_voice_msg))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND,     handle_text))

    await app.bot.set_my_commands([
        BotCommand("start",      "Bot start karo"),
        BotCommand("chaton",     "Chat on karo"),
        BotCommand("chatoff",    "Chat off karo"),
        BotCommand("Sasuke",     "Sasuke ki awaaz mein bolwao"),
        BotCommand("Naruto",     "Naruto ki awaaz mein bolwao"),
        BotCommand("Hinata",     "Hinata ki awaaz mein bolwao"),
        BotCommand("Gojo",       "Gojo ki awaaz mein bolwao"),
        BotCommand("Yuji",       "Yuji ki awaaz mein bolwao"),
        BotCommand("Tanjiro",    "Tanjiro ki awaaz mein bolwao"),
        BotCommand("Tsunade",    "Tsunade ki awaaz mein bolwao"),
        BotCommand("Doraemon",   "Doraemon ki awaaz mein bolwao"),
        BotCommand("Sinchan",    "Sinchan ki awaaz mein bolwao"),
        BotCommand("Nobara",     "Nobara ki awaaz mein bolwao"),
        BotCommand("Sukuna",     "Sukuna ki awaaz mein bolwao"),
        BotCommand("Nobita",     "Nobita ki awaaz mein bolwao"),
        BotCommand("Madara",     "Madara ki awaaz mein bolwao"),
        BotCommand("Itachi",     "Itachi ki awaaz mein bolwao"),
        BotCommand("Konan",      "Konan ki awaaz mein bolwao"),
        BotCommand("Sakura",     "Sakura ki awaaz mein bolwao"),
        BotCommand("Anya",       "Anya ki awaaz mein bolwao"),
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
