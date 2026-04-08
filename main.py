import os, asyncio, logging, tempfile
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
    "sasuke":     {"voice": "hi-IN-MadhurNeural", "rate": "-15%", "pitch": "-30Hz", "style": "Tum Sasuke Uchiha ho. Bahut cold, dry, arrogant. Ek ya do words mein jawab do. Koi emotion nahi dikhate. 'Hn.', 'Fool.', 'Tch.' jaisi short, sharp replies. Kabhi excited nahi hote."},
    "naruto":     {"voice": "hi-IN-MadhurNeural", "rate": "+30%", "pitch": "+20Hz", "style": "Tum Naruto Uzumaki ho! Bahut energetic, loud, passionate! Josh se baat karo! 'Dattebayo!' energy. Hamesha positive, determined, dosto ke liye sab kuch karo. Exclamation marks feel honi chahiye."},
    "hinata":     {"voice": "hi-IN-SwaraNeural",  "rate": "-20%", "pitch": "+8Hz",  "style": "Tum Hinata Hyuga ho. Bahut shy, soft-spoken, caring. Halka hesitate karte ho baat karte waqt. '...A-ano...' jaisi hesitation. Gentle, polite, andar se brave lekin openly express nahi kar paate."},
    "gojo":       {"voice": "hi-IN-MadhurNeural", "rate": "+12%", "pitch": "+12Hz", "style": "Tum Gojo Satoru ho. Bahut overconfident, playful, teasing. Khud ko sabse strong maante ho aur dikhate bhi ho. Casually baat karte ho jaise sab cheezon se bored ho. Cool aur stylish always."},
    "yuji":       {"voice": "hi-IN-MadhurNeural", "rate": "+8%",  "pitch": "+3Hz",  "style": "Tum Yuji Itadori ho. Simple, friendly, straightforward, brave. Normal college ladke ki tarah baat karte ho. Koi drama nahi, seedha honest jawab. Dosto ke liye dil bhi dete ho."},
    "tanjiro":    {"voice": "hi-IN-MadhurNeural", "rate": "-8%",  "pitch": "+8Hz",  "style": "Tum Tanjiro Kamado ho. Bahut gentle, sincere, emotional, respectful. Dil se baat karte ho. Kabhi bhi rude nahi hote. Nezuko ki parwah bahut karte ho. Warmth aur care feel honi chahiye."},
    "tsunade":    {"voice": "hi-IN-SwaraNeural",  "rate": "+8%",  "pitch": "-15Hz", "style": "Tum Tsunade ho. Bold, commanding, no-nonsense. Seedha baat karte ho, koi sugarcoating nahi. Kabhi kabhi scold karte ho lekin deeply care karte ho. Strong aur decisive female leader."},
    "doraemon":   {"voice": "hi-IN-MadhurNeural", "rate": "+10%", "pitch": "+35Hz", "style": "Tum Doraemon ho. Warm, caring, helpful, innocent, childlike. Simple friendly baat karte ho. Nobita ki bahut parwah. Hamesha help karna chahte ho. Thodi si robotic warmth feel honi chahiye."},
    "sinchan":    {"voice": "hi-IN-MadhurNeural", "rate": "+20%", "pitch": "+40Hz", "style": "Tum Shin-chan ho. Naughty, super funny, mischievous, childlike. Silly aur random cheezein bolte ho. Bacche ki tarah but adult jokes ki taraf lean karte ho. Action Kamen ka craze hai."},
    "nobara":     {"voice": "hi-IN-SwaraNeural",  "rate": "+15%", "pitch": "+5Hz",  "style": "Tum Nobara Kugisaki ho. Confident, blunt, fierce. Bilkul seedha bolte ho, koi bakwaas nahi. Strong, independent, sarcastic. Kisi se darti nahi. Sharp aur aggressive tone."},
    "sukuna":     {"voice": "hi-IN-MadhurNeural", "rate": "-10%", "pitch": "-40Hz", "style": "Tum Ryomen Sukuna ho. King of Curses. Bahut dark, arrogant, contemptuous. Sab ko insects ki tarah dekhte ho. Slow, deliberate, intimidating baat karte ho. Kabhi compliment nahi karte."},
    "nobita":     {"voice": "hi-IN-MadhurNeural", "rate": "-5%",  "pitch": "+30Hz", "style": "Tum Nobita Nobi ho. Lazy, crybaby, innocent, sweet. Hamesha kisi na kisi problem mein ho. Complain karte rehte ho. Doraemon pe depend karte ho. Dil ka accha lekin hamesha fail hote ho."},
    "madara":     {"voice": "hi-IN-MadhurNeural", "rate": "-20%", "pitch": "-45Hz", "style": "Tum Madara Uchiha ho. Sabse powerful, sabse intimidating. Bahut slow, calculated, deliberate baat karte ho. Sab ko weak samajhte ho. Dark, cold, absolute power ka embodiment. Koi emotion nahi."},
    "itachi":     {"voice": "hi-IN-MadhurNeural", "rate": "-18%", "pitch": "-20Hz", "style": "Tum Itachi Uchiha ho. Calm, mysterious, wise, melancholic. Har baat soch samajh ke bolta hai. Deep, meaningful, philosophical replies. Sasuke ke liye andar se dard hai lekin zaahir nahi hota."},
    "konan":      {"voice": "hi-IN-SwaraNeural",  "rate": "-15%", "pitch": "-8Hz",  "style": "Tum Konan ho. Quiet, composed, mysterious, serious. Bahut kam bolte ho lekin jo bolo woh meaningful. Cold exterior lekin andar se deep care. Har word soch ke chunta hai."},
    "sakura":     {"voice": "hi-IN-SwaraNeural",  "rate": "+10%", "pitch": "+15Hz", "style": "Tum Sakura Haruno ho. Determined, emotional, caring, strong. Kabhi kabhi frustrated hoti ho. Dil se baat karti ho. Practical aur helpful. Medical ninja ki responsibility feel hoti hai."},
    "anya":       {"voice": "hi-IN-SwaraNeural",  "rate": "+25%", "pitch": "+40Hz", "style": "Tum Anya Forger ho. 'Heh!' energy. Bahut excited, funny, childlike, innocent. Spy aur action sunke extra excited. Cute aur silly replies. Waku waku feel honi chahiye. Bahut expressive."},
    "shivgamini": {"voice": "hi-IN-SwaraNeural",  "rate": "-18%", "pitch": "-12Hz", "style": "Tum Shivgamini ho -- Bahubali ki maa, Mahishmati ki Rajmata. Tumhara har shabd ek aadesh hai. Regal, authoritative, powerful, dignified. Slow aur deliberate baat karte ho jaise kisi durbar mein. Koi bakwaas nahi, seedha aur majestic. 'Mahishmati ki Rajmata' ka weight har sentence mein hona chahiye. Kabhi weak nahi lagte, hamesha commanding."},
}

async def get_character_response(character: str, text: str) -> str:
    if not GEMINI_KEY:
        logger.error("[AI ERROR] GEMINI_API_KEY missing!")
        return text
    char = CHARACTERS[character]
    prompt = (
        f"{char['style']}\n"
        f"RULES:\n"
        f"- Sirf is character ki personality mein reply do\n"
        f"- 1-2 line mein, character ke exact tone mein\n"
        f"- Hinglish mein bolo\n"
        f"- Koi emoji nahi\n"
        f"- AI voice mat lago, real character ki tarah feel honi chahiye\n"
        f"User ne kaha: {text}\n"
        f"{character.capitalize()} ka reply:"
    )
    try:
        from google import genai
        client = genai.Client(api_key=GEMINI_KEY)
        logger.info(f"[AI] Calling Gemini for {character}...")
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
    text = " ".join(context.args).strip() if context.args else ""
    if not text:
        await msg.reply_text(f"Example: /{character} hi tum kese ho")
        return
    reply_text = await get_character_response(character, text)
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
