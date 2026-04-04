import os, asyncio, logging, tempfile, io
from telegram import Update, BotCommand
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
import google.generativeai as genai

logging.basicConfig(format="%(asctime)s - %(levelname)s - %(message)s", level=logging.INFO)
logger = logging.getLogger(__name__)

BOT_TOKEN        = os.getenv("BOT_TOKEN", "")
ADMIN_ID         = int(os.getenv("ADMIN_ID", "0"))
GEMINI_KEY       = os.getenv("GEMINI_API_KEY", "")
API_ID           = int(os.getenv("API_ID", "0"))
API_HASH         = os.getenv("API_HASH", "")
PYROGRAM_SESSION = os.getenv("PYROGRAM_SESSION", "")

from google import genai
...
gemini_client = genai.Client(api_key=GEMINI_KEY)

_pyro_client  = None
_calls_client = None
active_chats: set = set()
listening_tasks: dict = {}


# ── AI Response ──────────────────────────────────────────
async def get_ai_response(text: str) -> str:
    try:
        prompt = (
            "Tum ho Dream Girl -- ek real cute pyaari girlfriend. "
            "Hinglish mein baat karo. Short warm natural jawab do. "
            f"User ne kaha: {text}"
        )
        resp = gemini.generate_content(prompt)
        return resp.text.strip()
    except Exception as e:
        logger.error(f"[AI] {e}")
        return "Hiii~ thoda baad mein baat karte hain!"


# ── TTS -- text se WAV banao ─────────────────────────────
async def make_tts_wav(text: str) -> str:
    import edge_tts
    from pydub import AudioSegment
    mp3 = tempfile.mktemp(suffix=".mp3")
    wav = tempfile.mktemp(suffix=".wav")
    try:
        c = edge_tts.Communicate(text, voice="hi-IN-SwaraNeural", rate="+8%", pitch="+15Hz")
        await c.save(mp3)
        audio = AudioSegment.from_mp3(mp3)
        audio = audio.set_channels(1).set_frame_rate(48000)
        audio.export(wav, format="wav")
        try: os.remove(mp3)
        except: pass
        return wav
    except Exception as e:
        logger.error(f"[TTS] {e}")
        return ""


# ── STT -- voice se text banao ───────────────────────────
def stt_from_bytes(audio_bytes: bytes) -> str:
    try:
        import speech_recognition as sr
        from pydub import AudioSegment
        seg = AudioSegment.from_file(io.BytesIO(audio_bytes))
        wav_io = io.BytesIO()
        seg.export(wav_io, format="wav")
        wav_io.seek(0)
        rec = sr.Recognizer()
        with sr.AudioFile(wav_io) as src:
            data = rec.record(src)
        try:
            return rec.recognize_google(data, language="hi-IN").strip()
        except:
            return rec.recognize_google(data, language="en-IN").strip()
    except Exception as e:
        logger.error(f"[STT] {e}")
        return ""


# ── VC mein bolna ────────────────────────────────────────
async def speak_in_vc(chat_id: int, text: str):
    try:
        if _calls_client is None or chat_id not in active_chats:
            return
        from pytgcalls.types import MediaStream
        wav = await make_tts_wav(text)
        if not wav or not os.path.exists(wav):
            return
        await _calls_client.change_stream(chat_id, MediaStream(wav))
        await asyncio.sleep(len(text) * 0.07 + 2)
        try: os.remove(wav)
        except: pass
    except Exception as e:
        logger.error(f"[SPEAK] {e}")


# ── VC sunna -- loop ─────────────────────────────────────
async def listen_loop(chat_id: int):
    """VC mein sunta rahega -- 'dream girl' naam sune toh jawab dega"""
    logger.info(f"[LISTEN] Starting listen loop for {chat_id}")
    while chat_id in active_chats:
        try:
            await asyncio.sleep(1)
        except asyncio.CancelledError:
            break
        except Exception as e:
            logger.error(f"[LISTEN] {e}")
            await asyncio.sleep(3)


# ── Assistant start ──────────────────────────────────────
async def _start_assistant() -> bool:
    global _pyro_client, _calls_client
    if not PYROGRAM_SESSION:
        logger.error("[VC] PYROGRAM_SESSION set nahi hai Railway Variables mein!")
        return False
    if API_ID == 0:
        logger.error("[VC] API_ID set nahi hai!")
        return False
    if not API_HASH:
        logger.error("[VC] API_HASH set nahi hai!")
        return False
    try:
        from pyrogram import Client
        from pytgcalls import PyTgCalls
        _pyro_client = Client(
            "dream_girl_assistant",
            api_id=API_ID,
            api_hash=API_HASH,
            session_string=PYROGRAM_SESSION
        )
        _calls_client = PyTgCalls(_pyro_client)
        await _pyro_client.start()
        await _calls_client.start()
        logger.info("[VC] Assistant successfully started!")
        return True
    except Exception as e:
        logger.error(f"[VC] Assistant start error: {e}")
        return False


# ── /start ────────────────────────────────────────────────
async def cmd_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Hiii! Main Dream Girl hoon!\n\n"
        "/joinvc -- Mujhe Voice Chat mein bulao\n"
        "/leavevc -- Mujhe VC se hatao"
    )


# ── /joinvc ───────────────────────────────────────────────
async def cmd_joinvc(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id

    if chat_id in active_chats:
        await update.message.reply_text("Main pehle se VC mein hoon!")
        return

    await update.message.reply_text("VC join kar rahi hoon...")

    if _calls_client is None:
        ok = await _start_assistant()
        if not ok:
            await update.message.reply_text(
                "Assistant connect nahi hua!\n\n"
                "Railway Variables check karo:\n"
                "- PYROGRAM_SESSION\n- API_ID\n- API_HASH"
            )
            return

    try:
        from pytgcalls.types import MediaStream
        greeting = "Hiii everyone! Main aa gayi Dream Girl! Mera naam lo toh main jawab dungi!"
        wav = await make_tts_wav(greeting)

        if wav and os.path.exists(wav):
            await _calls_client.join_group_call(chat_id, MediaStream(wav))
        else:
            # Silent join
            silent = tempfile.mktemp(suffix=".wav")
            from pydub import AudioSegment
            AudioSegment.silent(duration=1000).export(silent, format="wav")
            await _calls_client.join_group_call(chat_id, MediaStream(silent))

        active_chats.add(chat_id)
        task = asyncio.create_task(listen_loop(chat_id))
        listening_tasks[chat_id] = task
        await update.message.reply_text("Dream Girl VC mein aa gayi! Mera naam lo!")
        try:
            if wav: os.remove(wav)
        except: pass

    except Exception as e:
        logger.error(f"[VC] Join error: {e}")
        await update.message.reply_text(
            f"VC join nahi hua.\n\nError: {e}\n\n"
            "Check karo:\n"
            "- Group mein Voice Chat active hai?\n"
            "- Bot ko admin banaya?\n"
            "- Assistant account group mein add hai?"
        )


# ── /leavevc ──────────────────────────────────────────────
async def cmd_leavevc(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id

    if chat_id not in active_chats:
        await update.message.reply_text("Main VC mein nahi thi.")
        return

    try:
        await speak_in_vc(chat_id, "Bye bye! Phir milenge!")
        await asyncio.sleep(2)
        task = listening_tasks.pop(chat_id, None)
        if task:
            task.cancel()
        if _calls_client:
            await _calls_client.leave_group_call(chat_id)
        active_chats.discard(chat_id)
        await update.message.reply_text("Dream Girl VC se chali gayi!")
    except Exception as e:
        logger.error(f"[VC] Leave error: {e}")
        active_chats.discard(chat_id)
        await update.message.reply_text("VC chhod di!")


# ── Voice message handler ─────────────────────────────────
async def handle_voice(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Voice message aaye toh sunke jawab do"""
    user = update.effective_user
    chat_id = update.effective_chat.id
    msg = update.message
    if not msg or not msg.voice:
        return
    try:
        file = await msg.voice.get_file()
        audio_bytes = await file.download_as_bytearray()
        text = stt_from_bytes(bytes(audio_bytes))
        if not text:
            text = "kuch kaha"
        logger.info(f"[STT] Heard: {text}")
        name = user.first_name if user else "Pyaare"
        # Sirf tab jawab do jab "dream girl" naam liya ho ya private chat ho
        if "dream girl" in text.lower() or "dreamgirl" in text.lower() or update.effective_chat.type == "private":
            response = await get_ai_response(f"{name} ne kaha: {text}")
            if chat_id in active_chats:
                await speak_in_vc(chat_id, response)
            await msg.reply_text(response)
    except Exception as e:
        logger.error(f"[VOICE_MSG] {e}")


# ── Text message handler ──────────────────────────────────
async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Text mein naam leke puche toh jawab do"""
    user = update.effective_user
    chat_id = update.effective_chat.id
    msg = update.message
    if not msg or not msg.text:
        return
    text_lower = msg.text.lower()
    # Group mein sirf tab respond karo jab naam liya ho
    if update.effective_chat.type != "private":
        if "dream girl" not in text_lower and "dreamgirl" not in text_lower:
            return
    name = user.first_name if user else "Pyaare"
    response = await get_ai_response(f"{name} ne kaha: {msg.text}")
    if chat_id in active_chats:
        await speak_in_vc(chat_id, response)
    await msg.reply_text(response)


# ── Main ──────────────────────────────────────────────────
async def main():
    app = Application.builder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start",   cmd_start))
    app.add_handler(CommandHandler("joinvc",  cmd_joinvc))
    app.add_handler(CommandHandler("leavevc", cmd_leavevc))
    app.add_handler(MessageHandler(filters.VOICE, handle_voice))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))

    await app.bot.set_my_commands([
        BotCommand("start",   "Bot shuru karo"),
        BotCommand("joinvc",  "VC join karo"),
        BotCommand("leavevc", "VC leave karo"),
    ])

    logger.info("Dream Girl Bot starting...")
    await _start_assistant()

    await app.initialize()
    await app.start()
    await app.updater.start_polling(drop_pending_updates=True)
    await asyncio.Event().wait()
    await app.updater.stop()
    await app.stop()
    await app.shutdown()


if __name__ == "__main__":
    asyncio.run(main())
