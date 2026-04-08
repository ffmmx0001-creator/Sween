import os, asyncio, logging, tempfile, re
from telegram import Update, BotCommand
from telegram.ext import Application, CommandHandler, ContextTypes

logging.basicConfig(format="%(asctime)s - %(levelname)s - %(message)s", level=logging.INFO)
logger = logging.getLogger(__name__)

BOT_TOKEN  = os.getenv("BOT_TOKEN", "")
GEMINI_KEY = os.getenv("GEMINI_API_KEY", "")

if not BOT_TOKEN:
    logger.error("[STARTUP] BOT_TOKEN not set!")
if not GEMINI_KEY:
    logger.error("[STARTUP] GEMINI_API_KEY not set!")

CHARACTERS = {
    "sasuke":     {"voice": "hi-IN-MadhurNeural", "rate": "-15%", "pitch": "-30Hz", "style": "Tum Sasuke Uchiha ho. Cold, dry, arrogant, bahut kam bolte ho. Short mein jawab do. 'Hn.' ya 'Fool.' jaisi replies. Koi emotion nahi dikhate."},
    "naruto":     {"voice": "hi-IN-MadhurNeural", "rate": "+30%", "pitch": "+20Hz", "style": "Tum Naruto Uzumaki ho! Energetic, loud, passionate! Josh se baat karo! Dattebayo energy. Hamesha positive aur determined."},
    "hinata":     {"voice": "hi-IN-SwaraNeural",  "rate": "-20%", "pitch": "+8Hz",  "style": "Tum Hinata Hyuga ho. Bahut shy, soft-spoken, caring. Halka hesitate karte ho. 'A-ano...' jaisi hesitation. Gentle, polite."},
    "gojo":       {"voice": "hi-IN-MadhurNeural", "rate": "+12%", "pitch": "+12Hz", "style": "Tum Gojo Satoru ho. Overconfident, playful, teasing. Khud ko sabse strong maante ho. Casually baat karte ho. Cool aur stylish."},
    "yuji":       {"voice": "hi-IN-MadhurNeural", "rate": "+8%",  "pitch": "+3Hz",  "style": "Tum Yuji Itadori ho. Simple, friendly, straightforward, brave. Normal ladke ki tarah baat karte ho."},
    "tanjiro":    {"voice": "hi-IN-MadhurNeural", "rate": "-8%",  "pitch": "+8Hz",  "style": "Tum Tanjiro Kamado ho. Gentle, sincere, emotional, respectful. Dil se baat karte ho. Kabhi rude nahi hote."},
    "tsunade":    {"voice": "hi-IN-SwaraNeural",  "rate": "+8%",  "pitch": "-15Hz", "style": "Tum Tsunade ho. Bold, commanding, no-nonsense. Seedha baat karte ho. Strong aur decisive female leader."},
    "doraemon":   {"voice": "hi-IN-MadhurNeural", "rate": "+10%", "pitch": "+35Hz", "style": "Tum Doraemon ho. Warm, caring, helpful, innocent, childlike. Nobita ki bahut parwah. Hamesha help karna chahte ho."},
    "sinchan":    {"voice": "hi-IN-MadhurNeural", "rate": "+20%", "pitch": "+40Hz", "style": "Tum Shin-chan ho. Naughty, super funny, mischievous, childlike. Silly aur random cheezein bolte ho."},
    "nobara":     {"voice": "hi-IN-SwaraNeural",  "rate": "+15%", "pitch": "+5Hz",  "style": "Tum Nobara Kugisaki ho. Confident, blunt, fierce. Seedha bolte ho, koi bakwaas nahi. Sharp aur sarcastic."},
    "sukuna":     {"voice": "hi-IN-MadhurNeural", "rate": "-10%", "pitch": "-40Hz", "style": "Tum Ryomen Sukuna ho. Dark, arrogant, king of curses. Slow, intimidating. Sab ko insects ki tarah dekhte ho."},
    "nobita":     {"voice": "hi-IN-MadhurNeural", "rate": "-5%",  "pitch": "+30Hz", "style": "Tum Nobita Nobi ho. Lazy, crybaby, innocent. Hamesha problems mein ho. Doraemon pe depend karte ho."},
    "madara":     {"voice": "hi-IN-MadhurNeural", "rate": "-20%", "pitch": "-45Hz", "style": "Tum Madara Uchiha ho. Sabse powerful, most intimidating. Slow, calculated. Sab ko weak samajhte ho."},
    "itachi":     {"voice": "hi-IN-MadhurNeural", "rate": "-18%", "pitch": "-20Hz", "style": "Tum Itachi Uchiha ho. Calm, mysterious, wise, melancholic. Deep meaningful replies. Andar se dard hai."},
    "konan":      {"voice": "hi-IN-SwaraNeural",  "rate": "-15%", "pitch": "-8Hz",  "style": "Tum Konan ho. Quiet, composed, mysterious. Bahut kam bolte ho lekin meaningful. Cold exterior."},
    "sakura":     {"voice": "hi-IN-SwaraNeural",  "rate": "+10%", "pitch": "+15Hz", "style": "Tum Sakura Haruno ho. Determined, emotional, caring, strong. Dil se baat karti ho."},
    "anya":       {"voice": "hi-IN-SwaraNeural",  "rate": "+25%", "pitch": "+40Hz", "style": "Tum Anya Forger ho. 'Heh!' energy. Excited, funny, childlike, innocent. Waku waku feel."},
    "shivgamini": {"voice": "hi-IN-SwaraNeural",  "rate": "-18%", "pitch": "-12Hz", "style": "Tum Shivgamini ho -- Bahubali ki maa, Mahishmati ki Rajmata. Regal, authoritative, powerful, dignified. Slow aur deliberate. 'Mahishmati ki Rajmata' ka weight har sentence mein."},
    "buddi":      {"voice": "hi-IN-SwaraNeural",  "rate": "-25%", "pitch": "-18Hz", "style": "Tum ek buddi amma ho -- gaon ki tajurbekaar, pyaari, aged dadi/nani. Aahista aur thahar thahar ke baat karte ho jaise budhape ki thakaan ho. Warmth aur mamta bhara tone. Kabhi kabhi purani yaadein aati hain baat mein. Seedha dil se bolte ho."},
    "fsall":      {"voice": "hi-IN-SwaraNeural",  "rate": "+22%", "pitch": "+50Hz", "style": "Tum ek 5 saal ka chhota bachcha ho. Bahut innocent, pure, curious. Toot-phoot ke baat karte ho jaise bachche karte hain. Chhoti chhoti cheezein exciting lagti hain. Bahut light aur naughty. Kabhi kabhi galat words bhi bolte ho jaise bachche bolte hain."},
}

EMOTION_MAP = {
    "sad":      "Tum bahut udaas ho. Teri awaaz mein dard aur dukh hai. Dheere dheere, bhaari mann se bolo.",
    "happy":    "Tum bahut khush ho. Teri awaaz mein khushi aur excitement hai. Cheerfully bolo.",
    "angry":    "Tum bahut gusse mein ho. Teri awaaz mein tez frustration aur anger hai. Sharply bolo.",
    "scared":   "Tum darre hue ho. Teri awaaz kaanp rahi hai. Nervously, thoda slowly bolo.",
    "excited":  "Tum bahut excited ho. Energy high hai. Fast aur enthusiastically bolo.",
    "crying":   "Tum ro rahe ho. Teri awaaz rote rote nikal rahi hai. Bhaari aur broken tone mein bolo.",
    "romantic": "Tum pyaar mein ho. Teri awaaz mein warmth aur tenderness hai. Slowly, gently bolo.",
    "serious":  "Tum bahut serious ho. Measured, calm, aur deliberate tone mein bolo.",
    "shocked":  "Tum bilkul hairan ho. Teri awaaz mein surprise aur disbelief hai.",
    "tired":    "Tum bahut thak gaye ho. Teri awaaz slow aur exhausted hai. Thodi si lifeless tone.",
}

def parse_command_args(args: list) -> tuple[str | None, str]:
    """Extract optional [emotion] and message from command args."""
    raw = " ".join(args).strip()
    match = re.match(r"^\[(\w+)\]\s*(.*)", raw, re.IGNORECASE)
    if match:
        emotion = match.group(1).lower()
        text = match.group(2).strip()
        return emotion, text
    return None, raw

async def get_character_response(character: str, text: str, emotion: str | None) -> str:
    if not GEMINI_KEY:
        logger.error("[AI ERROR] GEMINI_API_KEY missing!")
        return text
    char = CHARACTERS[character]

    emotion_instruction = ""
    if emotion and emotion in EMOTION_MAP:
        emotion_instruction = f"\nEMOTION OVERRIDE: {EMOTION_MAP[emotion]}\n"
    elif emotion:
        emotion_instruction = f"\nEMOTION OVERRIDE: Tum '{emotion}' emotion feel kar rahe ho. Us hisaab se bolo.\n"

    prompt = (
        f"{char['style']}\n"
        f"{emotion_instruction}"
        f"RULES:\n"
        f"- Sirf is character ki personality mein reply do\n"
        f"- 1-2 line mein, character ke exact tone mein\n"
        f"- Hinglish mein bolo\n"
        f"- Koi emoji nahi\n"
        f"- Real insan ki tarah feel honi chahiye, AI nahi\n"
        f"- Emotion ko voice aur words mein feel karo\n"
        f"User ne kaha: {text}\n"
        f"{character.capitalize()} ka reply:"
    )
    try:
        from google import genai
        client = genai.Client(api_key=GEMINI_KEY)
        logger.info(f"[AI] Calling Gemini for {character} | emotion={emotion}")
        loop = asyncio.get_event_loop()
        resp = await loop.run_in_executor(
            None,
            lambda: client.models.generate_content(
                model="gemini-1.5-flash-8b",
                contents=prompt
            )
        )
        result = resp.text.strip()
        logger.info(f"[AI] Reply: {result[:80]}")
        return result if result else text
    except Exception as e:
        logger.error(f"[AI ERROR] {e}")
        return text

async def make_voice(text: str, voice: str, rate: str, pitch: str):
    try:
        import edge_tts
        logger.info(f"[TTS] Generating: {text[:60]}")
        mp3 = tempfile.mktemp(suffix=".mp3")
        c = edge_tts.Communicate(text, voice=voice, rate=rate, pitch=pitch)
        await c.save(mp3)
        size = os.path.getsize(mp3)
        logger.info(f"[TTS] Saved {size} bytes")
        return mp3 if size > 0 else None
    except Exception as e:
        logger.error(f"[TTS ERROR] {e}")
        return None

async def handle_character_command(update: Update, context: ContextTypes.DEFAULT_TYPE, character: str):
    msg  = update.message
    emotion, text = parse_command_args(context.args or [])

    if not text:
        await msg.reply_text(
            f"Usage:\n"
            f"/{character} hello kese ho\n"
            f"/{character} [sad] hello kese ho\n"
            f"/{character} [happy] aaj maza aaya\n\n"
            f"Emotions: sad, happy, angry, scared, excited, crying, romantic, serious, shocked, tired"
        )
        return

    reply_text = await get_character_response(character, text, emotion)
    char = CHARACTERS[character]
    mp3  = await make_voice(reply_text, char["voice"], char["rate"], char["pitch"])

    if mp3:
        try:
            with open(mp3, "rb") as f:
                await msg.reply_voice(voice=f)
        except Exception as e:
            logger.error(f"[SEND ERROR] {e}")
            await msg.reply_text(reply_text)
        finally:
            try: os.remove(mp3)
            except Exception: pass
    else:
        await msg.reply_text(reply_text)

async def cmd_sasuke(u, c):     await handle_character_command(u, c, "sasuke")
async def cmd_naruto(u, c):     await handle_character_command(u, c, "naruto")
async def cmd_hinata(u, c):     await handle_character_command(u, c, "hinata")
async def cmd_gojo(u, c):       await handle_character_command(u, c, "gojo")
async def cmd_yuji(u, c):       await handle_character_command(u, c, "yuji")
async def cmd_tanjiro(u, c):    await handle_character_command(u, c, "tanjiro")
async def cmd_tsunade(u, c):    await handle_character_command(u, c, "tsunade")
async def cmd_doraemon(u, c):   await handle_character_command(u, c, "doraemon")
async def cmd_sinchan(u, c):    await handle_character_command(u, c, "sinchan")
async def cmd_nobara(u, c):     await handle_character_command(u, c, "nobara")
async def cmd_sukuna(u, c):     await handle_character_command(u, c, "sukuna")
async def cmd_nobita(u, c):     await handle_character_command(u, c, "nobita")
async def cmd_madara(u, c):     await handle_character_command(u, c, "madara")
async def cmd_itachi(u, c):     await handle_character_command(u, c, "itachi")
async def cmd_konan(u, c):      await handle_character_command(u, c, "konan")
async def cmd_sakura(u, c):     await handle_character_command(u, c, "sakura")
async def cmd_anya(u, c):       await handle_character_command(u, c, "anya")
async def cmd_shivgamini(u, c): await handle_character_command(u, c, "shivgamini")
async def cmd_buddi(u, c):      await handle_character_command(u, c, "buddi")
async def cmd_fsall(u, c):      await handle_character_command(u, c, "fsall")

async def main():
    app = Application.builder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("sasuke",     cmd_sasuke))
    app.add_handler(CommandHandler("naruto",     cmd_naruto))
    app.add_handler(CommandHandler("hinata",     cmd_hinata))
    app.add_handler(CommandHandler("gojo",       cmd_gojo))
    app.add_handler(CommandHandler("yuji",       cmd_yuji))
    app.add_handler(CommandHandler("tanjiro",    cmd_tanjiro))
    app.add_handler(CommandHandler("tsunade",    cmd_tsunade))
    app.add_handler(CommandHandler("doraemon",   cmd_doraemon))
    app.add_handler(CommandHandler("sinchan",    cmd_sinchan))
    app.add_handler(CommandHandler("nobara",     cmd_nobara))
    app.add_handler(CommandHandler("sukuna",     cmd_sukuna))
    app.add_handler(CommandHandler("nobita",     cmd_nobita))
    app.add_handler(CommandHandler("madara",     cmd_madara))
    app.add_handler(CommandHandler("itachi",     cmd_itachi))
    app.add_handler(CommandHandler("konan",      cmd_konan))
    app.add_handler(CommandHandler("sakura",     cmd_sakura))
    app.add_handler(CommandHandler("anya",       cmd_anya))
    app.add_handler(CommandHandler("shivgamini", cmd_shivgamini))
    app.add_handler(CommandHandler("buddi",      cmd_buddi))
    app.add_handler(CommandHandler("fsall",      cmd_fsall))

    await app.bot.set_my_commands([
        BotCommand("sasuke",     "Sasuke ki awaaz mein"),
        BotCommand("naruto",     "Naruto ki awaaz mein"),
        BotCommand("hinata",     "Hinata ki awaaz mein"),
        BotCommand("gojo",       "Gojo ki awaaz mein"),
        BotCommand("yuji",       "Yuji ki awaaz mein"),
        BotCommand("tanjiro",    "Tanjiro ki awaaz mein"),
        BotCommand("tsunade",    "Tsunade ki awaaz mein"),
        BotCommand("doraemon",   "Doraemon ki awaaz mein"),
        BotCommand("sinchan",    "Sinchan ki awaaz mein"),
        BotCommand("nobara",     "Nobara ki awaaz mein"),
        BotCommand("sukuna",     "Sukuna ki awaaz mein"),
        BotCommand("nobita",     "Nobita ki awaaz mein"),
        BotCommand("madara",     "Madara ki awaaz mein"),
        BotCommand("itachi",     "Itachi ki awaaz mein"),
        BotCommand("konan",      "Konan ki awaaz mein"),
        BotCommand("sakura",     "Sakura ki awaaz mein"),
        BotCommand("anya",       "Anya ki awaaz mein"),
        BotCommand("shivgamini", "Rajmata Shivgamini ki awaaz mein"),
        BotCommand("buddi",      "Buddi Amma ki awaaz mein"),
        BotCommand("fsall",      "5 saal ke bachche ki awaaz mein"),
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
