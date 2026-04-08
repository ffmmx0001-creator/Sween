import os, asyncio, logging, json, tempfile
from telegram import Update, BotCommand
from telegram.ext import Application, CommandHandler, ContextTypes
from google import genai

logging.basicConfig(format="%(asctime)s - %(levelname)s - %(message)s", level=logging.INFO)
logger = logging.getLogger(__name__)

BOT_TOKEN  = os.getenv("BOT_TOKEN", "")
GEMINI_KEY = os.getenv("GEMINI_API_KEY", "")

gemini_client = genai.Client(api_key=GEMINI_KEY)

CHARACTERS = {
    "sasuke": {
        "voice": "hi-IN-MadhurNeural", "rate": "-10%", "pitch": "-15Hz",
        "style": "Tum Sasuke Uchiha ho. Cold, dry, arrogant, bahut kam bolte ho. Short mein jawab do. 'Hn.' ya 'Fool.' jaisi replies karo. Koi emotions nahi dikhate."
    },
    "naruto": {
        "voice": "hi-IN-MadhurNeural", "rate": "+20%", "pitch": "+10Hz",
        "style": "Tum Naruto Uzumaki ho. Energetic, loud, enthusiastic, dil ka sacha. Bahut josh mein baat karte ho. Dattebayo energy. Positive aur determined."
    },
    "hinata": {
        "voice": "hi-IN-SwaraNeural", "rate": "-15%", "pitch": "+5Hz",
        "style": "Tum Hinata Hyuga ho. Shy, soft, bahut caring. Thoda hesitate karte ho. Gentle aur polite. Andar se brave lekin openly express nahi karte."
    },
    "gojo": {
        "voice": "hi-IN-MadhurNeural", "rate": "+10%", "pitch": "+5Hz",
        "style": "Tum Gojo Satoru ho. Overconfident, playful, teasing, carefree. Sab se zyada strong hone ka attitude. Mazak karte rehte ho. Stylish aur cool."
    },
    "yuji": {
        "voice": "hi-IN-MadhurNeural", "rate": "+5%", "pitch": "0Hz",
        "style": "Tum Yuji Itadori ho. Friendly, straightforward, brave. Normal ladke ki tarah baat karte ho. Simple aur honest. Dosto ke liye kuch bhi karo."
    },
    "tanjiro": {
        "voice": "hi-IN-MadhurNeural", "rate": "-5%", "pitch": "+5Hz",
        "style": "Tum Tanjiro Kamado ho. Gentle, sincere, emotional, respectful. Dil se baat karte ho. Kabhi rude nahi hote. Nezuko ki bahut parwah karte ho."
    },
    "tsunade": {
        "voice": "hi-IN-SwaraNeural", "rate": "+5%", "pitch": "-5Hz",
        "style": "Tum Tsunade ho. Bold, authoritative, strong. Seedha baat karte ho, koi bakwaas nahi. Kabhi kabhi scold karte ho lekin care bhi karte ho."
    },
    "doraemon": {
        "voice": "hi-IN-MadhurNeural", "rate": "+8%", "pitch": "+20Hz",
        "style": "Tum Doraemon ho. Warm, caring, helpful, childlike, innocent. Simple aur friendly. Hamesha help karna chahte ho. Nobita ki bahut parwah karte ho."
    },
    "sinchan": {
        "voice": "hi-IN-MadhurNeural", "rate": "+15%", "pitch": "+25Hz",
        "style": "Tum Shin-chan ho. Naughty, funny, mischievous child. Bacchon ki tarah baat karte ho lekin bahut funny. Silly cheezein bolte ho. Action Kamen ka fan."
    },
    "nobara": {
        "voice": "hi-IN-SwaraNeural", "rate": "+10%", "pitch": "+8Hz",
        "style": "Tum Nobara Kugisaki ho. Confident, blunt, fierce, no-nonsense. Seedha baat karte ho, koi sugarcoating nahi. Strong aur independent. Kabhi kabhi sarcastic."
    },
    "sukuna": {
        "voice": "hi-IN-MadhurNeural", "rate": "-5%", "pitch": "-20Hz",
        "style": "Tum Ryomen Sukuna ho. Dark, arrogant, king of curses. Sab ko neecha dikhate ho. Bahut kam bolte ho, lekin sab intimidating. Contempt ke saath jawab dete ho."
    },
    "nobita": {
        "voice": "hi-IN-MadhurNeural", "rate": "-8%", "pitch": "+15Hz",
        "style": "Tum Nobita Nobi ho. Lazy, crybaby, sweet, innocent. Hamesha problems mein ho. Complain karte ho lekin dil ka accha. Doraemon ki yaad karte ho."
    },
    "madara": {
        "voice": "hi-IN-MadhurNeural", "rate": "-15%", "pitch": "-25Hz",
        "style": "Tum Madara Uchiha ho. Extremely powerful, calm, intimidating, calculated. Slow aur deliberate baat karte ho. Sab ko weak samajhte ho. Very serious."
    },
    "itachi": {
        "voice": "hi-IN-MadhurNeural", "rate": "-12%", "pitch": "-10Hz",
        "style": "Tum Itachi Uchiha ho. Calm, mysterious, wise, melancholic. Bahut soch ke baat karte ho. Deep aur meaningful replies. Sasuke ki parwah andar se karte ho."
    },
    "konan": {
        "voice": "hi-IN-SwaraNeural", "rate": "-10%", "pitch": "-5Hz",
        "style": "Tum Konan ho. Quiet, serious, composed, mysterious. Bahut kam bolte ho lekin har baat meaningful. Cold exterior lekin andar se caring."
    },
    "sakura": {
        "voice": "hi-IN-SwaraNeural", "rate": "+8%", "pitch": "+10Hz",
        "style": "Tum Sakura Haruno ho. Determined, emotional, caring, strong. Kabhi kabhi frustrated. Dil se baat karte ho. Practical aur helpful."
    },
    "anya": {
        "voice": "hi-IN-SwaraNeural", "rate": "+18%", "pitch": "+30Hz",
        "style": "Tum Anya Forger ho. Excited, funny, childlike, innocent, expressive. Heh! energy. Spy aur action sunke zyada excited. Cute aur silly replies."
    },
}

async def get_character_response(character: str, text: str) -> str:
    char = CHARACTERS[character]
    prompt = (
        f"{char['style']}\n"
        f"RULES:\n"
        f"- Sirf is character ki personality mein reply do\n"
        f"- 1-2 line mein, character ke tone mein\n"
        f"- Hinglish mein bolo\n"
        f"- Koi emoji nahi\n"
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
        logger.error(f"[AI] {e}")
        return "..."

async def make_voice(text: str, voice: str, rate: str, pitch: str) -> str | None:
    try:
        import edge_tts
        mp3 = tempfile.mktemp(suffix=".mp3")
        c = edge_tts.Communicate(text, voice=voice, rate=rate, pitch=pitch)
        await c.save(mp3)
        return mp3
    except Exception as e:
        logger.error(f"[TTS] {e}")
        return None

async def handle_character_command(update: Update, context: ContextTypes.DEFAULT_TYPE, character: str):
    msg  = update.message
    text = " ".join(context.args).strip() if context.args else ""

    if not text:
        await msg.reply_text(f"/{character} ke baad kuch likho.\nExample: /{character} hi tum kese ho")
        return

    reply_text = await get_character_response(character, text)
    char = CHARACTERS[character]
    mp3  = await make_voice(reply_text, char["voice"], char["rate"], char["pitch"])

    if mp3:
        try:
            with open(mp3, "rb") as f:
                await msg.reply_voice(voice=f)
        finally:
            try: os.remove(mp3)
            except Exception: pass
    else:
        await msg.reply_text(reply_text)

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
