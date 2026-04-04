import os, asyncio, logging
from telegram import Update, BotCommand
from telegram.ext import Application, CommandHandler, ContextTypes
import google.generativeai as genai

logging.basicConfig(
    format="%(asctime)s - %(levelname)s - %(message)s",
    level=logging.INFO
)
logger = logging.getLogger(__name__)

BOT_TOKEN         = os.getenv("BOT_TOKEN", "")
ADMIN_ID          = int(os.getenv("ADMIN_ID", "0"))
GEMINI_KEY        = os.getenv("GEMINI_API_KEY", "")
API_ID            = int(os.getenv("API_ID", "0"))
API_HASH          = os.getenv("API_HASH", "")
PYROGRAM_SESSION  = os.getenv("PYROGRAM_SESSION", "")

genai.configure(api_key=GEMINI_KEY)
gemini = genai.GenerativeModel("gemini-1.5-flash")

_pyro_client  = None
_calls_client = None
active_chats: set = set()


async def make_tts_wav(text: str) -> str:
    import tempfile, edge_tts
    from pydub import AudioSegment
    mp3 = tempfile.mktemp(suffix=".mp3")
    wav = tempfile.mktemp(suffix=".wav")
    try:
        c = edge_tts.Communicate(text, voice="hi-IN-SwaraNeural",
                                 rate="+8%", pitch="+15Hz")
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


async def _start_assistant():
    global _pyro_client, _calls_client
    if not PYROGRAM_SESSION:
        logger.error("[VC] PYROGRAM_SESSION Railway Variable mein set nahi hai!")
        return False
    try:
        from pyrogram import Client
        from pytgcalls import PyTgCalls
        _pyro_client  = Client(
            "assistant",
            api_id=API_ID,
            api_hash=API_HASH,
            session_string=PYROGRAM_SESSION
        )
        _calls_client = PyTgCalls(_pyro_client)
        await _pyro_client.start()
        await _calls_client.start()
        logger.info("[VC] Assistant client started!")
        return True
    except Exception as e:
        logger.error(f"[VC] Assistant start error: {e}")
        return False


async def cmd_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Hiii! Main Dream Girl hoon.\n\n"
        "/joinvc -- Mujhe Voice Chat mein bulao\n"
        "/leavevc -- Mujhe VC se hatao"
    )


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
                "Assistant session nahi mila!\n"
                "Railway Variables mein PYROGRAM_SESSION check karo."
            )
            return

    try:
        from pytgcalls.types import MediaStream
        wav = await make_tts_wav(
            "Hiii everyone! Main aa gayi Dream Girl!"
        )
        if wav and os.path.exists(wav):
            stream = MediaStream(wav)
        else:
            stream = MediaStream(audio_path="/dev/zero")

        await _calls_client.join_group_call(chat_id, stream)
        active_chats.add(chat_id)
        await update.message.reply_text("Dream Girl VC mein aa gayi!")
        try: os.remove(wav)
        except: pass
    except Exception as e:
        logger.error(f"[VC] Join error: {e}")
        await update.message.reply_text(
            f"VC join nahi hua.\n\nError: {e}\n\n"
            "Check karo:\n"
            "- Group mein Voice Chat active hai?\n"
            "- Bot ko admin banaya?\n"
            "- PYROGRAM_SESSION Railway Variable mein sahi hai?"
        )


async def cmd_leavevc(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id

    if chat_id not in active_chats:
        await update.message.reply_text("Main VC mein nahi thi.")
        return

    try:
        if _calls_client:
            await _calls_client.leave_group_call(chat_id)
        active_chats.discard(chat_id)
        await update.message.reply_text("Dream Girl VC se chali gayi!")
    except Exception as e:
        logger.error(f"[VC] Leave error: {e}")
        active_chats.discard(chat_id)
        await update.message.reply_text("VC chhod di!")


async def main():
    app = Application.builder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start",   cmd_start))
    app.add_handler(CommandHandler("joinvc",  cmd_joinvc))
    app.add_handler(CommandHandler("leavevc", cmd_leavevc))

    await app.bot.set_my_commands([
        BotCommand("start",   "Bot shuru karo"),
        BotCommand("joinvc",  "VC join karo"),
        BotCommand("leavevc", "VC leave karo"),
    ])

    logger.info("Dream Girl Bot starting...")

    # Bot start hote hi assistant bhi start karo
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
