import os, asyncio, logging, tempfile
from telegram import Update, BotCommand
from telegram.ext import Application, CommandHandler, ContextTypes
import edge_tts

logging.basicConfig(format="%(asctime)s - %(levelname)s - %(message)s", level=logging.INFO)
logger = logging.getLogger(__name__)

BOT_TOKEN = os.getenv("BOT_TOKEN", "")
if not BOT_TOKEN:
    logger.error("[STARTUP] BOT_TOKEN not set!")

CHARACTERS = {
    "sasuke":    {"voice": "hi-IN-MadhurNeural", "rate": "-15%", "pitch": "-20Hz"},
    "naruto":    {"voice": "hi-IN-MadhurNeural", "rate": "+25%", "pitch": "+12Hz"},
    "hinata":    {"voice": "hi-IN-SwaraNeural",  "rate": "-20%", "pitch": "+8Hz"},
    "gojo":      {"voice": "hi-IN-MadhurNeural", "rate": "+10%", "pitch": "+10Hz"},
    "yuji":      {"voice": "hi-IN-MadhurNeural", "rate": "+8%",  "pitch": "+3Hz"},
    "tanjiro":   {"voice": "hi-IN-MadhurNeural", "rate": "-8%",  "pitch": "+5Hz"},
    "tsunade":   {"voice": "hi-IN-SwaraNeural",  "rate": "+8%",  "pitch": "-12Hz"},
    "doraemon":  {"voice": "hi-IN-MadhurNeural", "rate": "+8%",  "pitch": "+30Hz"},
    "sinchan":   {"voice": "hi-IN-MadhurNeural", "rate": "+22%", "pitch": "+42Hz"},
    "nobara":    {"voice": "hi-IN-SwaraNeural",  "rate": "+15%", "pitch": "+5Hz"},
    "sukuna":    {"voice": "hi-IN-MadhurNeural", "rate": "-12%", "pitch": "-40Hz"},
    "nobita":    {"voice": "hi-IN-MadhurNeural", "rate": "-5%",  "pitch": "+28Hz"},
    "madara":    {"voice": "hi-IN-MadhurNeural", "rate": "-22%", "pitch": "-45Hz"},
    "itachi":    {"voice": "hi-IN-MadhurNeural", "rate": "-18%", "pitch": "-18Hz"},
    "konan":     {"voice": "hi-IN-SwaraNeural",  "rate": "-18%", "pitch": "-8Hz"},
    "sakura":    {"voice": "hi-IN-SwaraNeural",  "rate": "+10%", "pitch": "+12Hz"},
    "anya":      {"voice": "hi-IN-SwaraNeural",  "rate": "+25%", "pitch": "+38Hz"},
}

async def make_voice(text: str, voice: str, rate: str, pitch: str):
    try:
        mp3 = tempfile.mktemp(suffix=".mp3")
        c = edge_tts.Communicate(text, voice=voice, rate=rate, pitch=pitch)
        await c.save(mp3)
        if os.path.getsize(mp3) > 0:
            return mp3
        return None
    except Exception as e:
        logger.error(f"[TTS ERROR] {e}")
        return None

async def handle_character_command(update: Update, context: ContextTypes.DEFAULT_TYPE, character: str):
    msg  = update.message
    text = " ".join(context.args).strip() if context.args else ""

    if not text:
        await msg.reply_text(f"/{character} ke baad kuch likho.\nExample: /{character} hello kaise ho")
        return

    char = CHARACTERS[character]
    mp3  = await make_voice(text, char["voice"], char["rate"], char["pitch"])

    if mp3:
        try:
            with open(mp3, "rb") as f:
                await msg.reply_voice(voice=f)
        except Exception as e:
            logger.error(f"[SEND ERROR] {e}")
            await msg.reply_text(text)
        finally:
            try: os.remove(mp3)
            except: pass
    else:
        await msg.reply_text(text)

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

async def main():
    app = Application.builder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("sasuke",   cmd_sasuke))
    app.add_handler(CommandHandler("naruto",   cmd_naruto))
    app.add_handler(CommandHandler("hinata",   cmd_hinata))
    app.add_handler(CommandHandler("gojo",     cmd_gojo))
    app.add_handler(CommandHandler("yuji",     cmd_yuji))
    app.add_handler(CommandHandler("tanjiro",  cmd_tanjiro))
    app.add_handler(CommandHandler("tsunade",  cmd_tsunade))
    app.add_handler(CommandHandler("doraemon", cmd_doraemon))
    app.add_handler(CommandHandler("sinchan",  cmd_sinchan))
    app.add_handler(CommandHandler("nobara",   cmd_nobara))
    app.add_handler(CommandHandler("sukuna",   cmd_sukuna))
    app.add_handler(CommandHandler("nobita",   cmd_nobita))
    app.add_handler(CommandHandler("madara",   cmd_madara))
    app.add_handler(CommandHandler("itachi",   cmd_itachi))
    app.add_handler(CommandHandler("konan",    cmd_konan))
    app.add_handler(CommandHandler("sakura",   cmd_sakura))
    app.add_handler(CommandHandler("anya",     cmd_anya))

    await app.bot.set_my_commands([
        BotCommand("sasuke",   "Sasuke ki awaaz mein"),
        BotCommand("naruto",   "Naruto ki awaaz mein"),
        BotCommand("hinata",   "Hinata ki awaaz mein"),
        BotCommand("gojo",     "Gojo ki awaaz mein"),
        BotCommand("yuji",     "Yuji ki awaaz mein"),
        BotCommand("tanjiro",  "Tanjiro ki awaaz mein"),
        BotCommand("tsunade",  "Tsunade ki awaaz mein"),
        BotCommand("doraemon", "Doraemon ki awaaz mein"),
        BotCommand("sinchan",  "Sinchan ki awaaz mein"),
        BotCommand("nobara",   "Nobara ki awaaz mein"),
        BotCommand("sukuna",   "Sukuna ki awaaz mein"),
        BotCommand("nobita",   "Nobita ki awaaz mein"),
        BotCommand("madara",   "Madara ki awaaz mein"),
        BotCommand("itachi",   "Itachi ki awaaz mein"),
        BotCommand("konan",    "Konan ki awaaz mein"),
        BotCommand("sakura",   "Sakura ki awaaz mein"),
        BotCommand("anya",     "Anya ki awaaz mein"),
    ])

    logger.info("Bot starting...")
    await app.initialize()
    await app.start()
    await app.updater.start_polling(drop_pending_updates=True)
    await asyncio.Event().wait()
    await app.updater.stop()
    await app.stop()
    await app.shutdown()

if __name__ == "__main__":
    asyncio.run(main())
