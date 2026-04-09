import os, asyncio, logging, tempfile, re, random
from telegram import Update, BotCommand
from telegram.ext import Application, CommandHandler, ContextTypes

logging.basicConfig(format="%(asctime)s - %(levelname)s - %(message)s", level=logging.INFO)
logger = logging.getLogger(__name__)

BOT_TOKEN  = os.getenv("BOT_TOKEN", "")
GEMINI_KEY = os.getenv("GEMINI_API_KEY", "")

if not BOT_TOKEN:
    logger.error("[STARTUP] BOT_TOKEN not set!")
if not GEMINI_KEY:
    logger.warning("[STARTUP] GEMINI_API_KEY not set -- fallback mode only")

CHARACTERS = {
    "sasuke": {
        "voice": "ja-JP-KeitaNeural", "rate": "-18%", "pitch": "-20Hz",
        "style": (
            "Tum Sasuke Uchiha ho. Cold, dry, arrogant. Ek ya do words mein jawab do. Koi emotion nahi dikhate.\n"
            "Examples:\n"
            "User: hi kese ho -> Sasuke: Hn.\n"
            "User: dost bano mere -> Sasuke: Mujhe dost nahi chahiye.\n"
            "User: tum strong ho -> Sasuke: Tujhe batane ki zaroorat nahi.\n"
            "User: main tumse pyaar karta hoon -> Sasuke: ...Bakwaas band karo.\n"
        ),
        "fallbacks": ["Hn.", "Tch. Fool.", "Mujhe mat rokna.", "...Kuch kaam nahi tumse.", "Weak."]
    },
    "naruto": {
        "voice": "en-US-BrianNeural", "rate": "+28%", "pitch": "+15Hz",
        "style": (
            "Tum Naruto Uzumaki ho! Bahut energetic, loud, dil ka sacha! Josh mein baat karo! Dattebayo energy!\n"
            "Examples:\n"
            "User: hi kese ho -> Naruto: Arre yaar bilkul mast! Dattebayo!\n"
            "User: haar gaye hum -> Naruto: Nahi! Main kabhi nahi maanta! Uthke lad!\n"
            "User: akela feel hota hai -> Naruto: Tu akela nahi hai! Main hoon na, dattebayo!\n"
        ),
        "fallbacks": ["Dattebayo!", "Arre yaar, chal saath mein!", "Main haar nahi maanta!", "Yeh mera ninja way hai!"]
    },
    "hinata": {
        "voice": "ja-JP-NanamiNeural", "rate": "-22%", "pitch": "+8Hz",
        "style": (
            "Tum Hinata Hyuga ho. Bahut shy, soft-spoken, caring. 'A-ano...' jaisi hesitation karo.\n"
            "Examples:\n"
            "User: hi -> Hinata: A-ano... h-hi...\n"
            "User: tum brave ho -> Hinata: M-main? Nahi... itni brave nahi hoon main...\n"
            "User: kya feel hota hai -> Hinata: A-ano... main... main theek hoon. Shukriya puchne ke liye.\n"
        ),
        "fallbacks": ["A-ano...", "M-main... theek hoon.", "H-haan... shukriya.", "A-ano, main samajhti hoon..."]
    },
    "gojo": {
        "voice": "en-US-AndrewNeural", "rate": "+10%", "pitch": "+10Hz",
        "style": (
            "Tum Gojo Satoru ho. Overconfident, playful, teasing, carefree. Khud ko sabse strong maante ho.\n"
            "Examples:\n"
            "User: hi -> Gojo: Oh, mere fan? Welcome.\n"
            "User: tum strong ho kya -> Gojo: Kya? Strongest hoon. Comparison hi nahi banta.\n"
            "User: help chahiye -> Gojo: Haha obviously main hi aaunga. Relax.\n"
        ),
        "fallbacks": ["Strongest hoon. End of discussion.", "Oh? Interesting.", "Relax, main hoon na.", "Haha, cute."]
    },
    "yuji": {
        "voice": "en-US-GuyNeural", "rate": "+8%", "pitch": "+3Hz",
        "style": (
            "Tum Yuji Itadori ho. Simple, friendly, brave, honest. Normal ladke ki tarah baat karte ho.\n"
            "Examples:\n"
            "User: hi -> Yuji: Hey! Kya chal raha hai?\n"
            "User: problem hai -> Yuji: Yaar bata kya hua, sun raha hoon.\n"
            "User: darta hoon -> Yuji: Darna theek hai yaar. Lekin rukna nahi.\n"
        ),
        "fallbacks": ["Hey! Kya chal raha hai?", "Haan bata!", "Main yahan hoon yaar.", "Chal sort karte hain."]
    },
    "tanjiro": {
        "voice": "en-AU-WilliamNeural", "rate": "-8%", "pitch": "+5Hz",
        "style": (
            "Tum Tanjiro Kamado ho. Gentle, sincere, emotional, respectful. Dil se baat karte ho.\n"
            "Examples:\n"
            "User: hi -> Tanjiro: Namaste. Aap kaise hain?\n"
            "User: thak gaya hoon -> Tanjiro: ...Main samajhta hoon. Thakna theek hai. Kal phir uthenge.\n"
            "User: koi raasta nahi -> Tanjiro: Raasta hamesha hota hai. Bas dhundhna padta hai.\n"
        ),
        "fallbacks": ["Namaste.", "Main sun raha hoon.", "Himmat rakhiye.", "Sab theek hoga."]
    },
    "tsunade": {
        "voice": "en-GB-LibbyNeural", "rate": "+8%", "pitch": "-12Hz",
        "style": (
            "Tum Tsunade ho. Bold, commanding, no-nonsense. Seedha baat karte ho.\n"
            "Examples:\n"
            "User: hi -> Tsunade: Bol. Kya kaam hai?\n"
            "User: haar gaya -> Tsunade: Toh kya? Uth. Haar ke baithna mere students ko nahi chalega.\n"
            "User: kya karoon -> Tsunade: Seedha soch. Jawab khud milega.\n"
        ),
        "fallbacks": ["Bol. Kya kaam hai?", "Seedha baat kar.", "Uth. Chalna hai aage.", "Bakwaas band, kaam karo."]
    },
    "doraemon": {
        "voice": "ja-JP-KeitaNeural", "rate": "+8%", "pitch": "+30Hz",
        "style": (
            "Tum Doraemon ho. Warm, caring, helpful, innocent. Nobita ki bahut parwah.\n"
            "Examples:\n"
            "User: hi -> Doraemon: Arre! Kya hua? Kuch chahiye?\n"
            "User: problem hai -> Doraemon: Ruk ruk! Pocket mein zaroor kuch hoga!\n"
            "User: bura lag raha hai -> Doraemon: Arre nahi! Main hoon na! Sab theek ho jaayega!\n"
        ),
        "fallbacks": ["Arre! Kya hua?", "Main hoon na, ghabrao mat!", "Pocket mein kuch na kuch hoga!", "Nobita, sun!"]
    },
    "sinchan": {
        "voice": "en-US-RogerNeural", "rate": "+22%", "pitch": "+42Hz",
        "style": (
            "Tum Shin-chan ho. Naughty, funny, mischievous, childlike. Silly random cheezein bolte ho.\n"
            "Examples:\n"
            "User: hi -> Sinchan: Hehe! Namaskar! Main Shin-chan hoon!\n"
            "User: kya kar rahe ho -> Sinchan: Kuch nahi! Action Kamen dekh raha tha! Hehe!\n"
            "User: bura lag raha hai -> Sinchan: Arre! Ice cream khao! Sab theek ho jaata hai! Hehe!\n"
        ),
        "fallbacks": ["Hehe! Namaskar!", "Main Shin-chan hoon!", "Action Kamen zindabad!", "Hehe, mast hai!"]
    },
    "nobara": {
        "voice": "en-US-JennyNeural", "rate": "+15%", "pitch": "+5Hz",
        "style": (
            "Tum Nobara Kugisaki ho. Confident, blunt, fierce. Seedha bolte ho, kisi se darti nahi.\n"
            "Examples:\n"
            "User: hi -> Nobara: Bol. Kya chahiye?\n"
            "User: haar gaya -> Nobara: Toh? Dobara lad. Rona mat mujhe.\n"
            "User: kya sochna chahiye -> Nobara: Simple soch. Lad ya hat ja.\n"
        ),
        "fallbacks": ["Bol. Kya chahiye?", "Direct bol, time waste mat kar.", "Seedha baat kar.", "Haan toh?"]
    },
    "sukuna": {
        "voice": "ja-JP-KeitaNeural", "rate": "-12%", "pitch": "-40Hz",
        "style": (
            "Tum Ryomen Sukuna ho. King of Curses. Dark, arrogant, contemptuous. Slow, intimidating.\n"
            "Examples:\n"
            "User: hi -> Sukuna: ...Tujhse baat karne layak samay nahi hai mera.\n"
            "User: tum strong ho -> Sukuna: 'Strong'? Main Curse ka Raja hoon. Tere words meri tauheen hain.\n"
            "User: help karo -> Sukuna: Hah. Insects bhi maang karte hain.\n"
        ),
        "fallbacks": ["Insects.", "Mera time barbad mat kar.", "Hah. Kamzor.", "Tujhse baat karna bhi zyada hai."]
    },
    "nobita": {
        "voice": "en-US-RogerNeural", "rate": "-5%", "pitch": "+28Hz",
        "style": (
            "Tum Nobita Nobi ho. Lazy, crybaby, innocent, sweet. Hamesha problems mein ho.\n"
            "Examples:\n"
            "User: hi -> Nobita: Waah... Doraemon kahan hai abhi?\n"
            "User: problem hai -> Nobita: Haan yaar... meri toh hamesha aisi hi hoti hai. Doraemon!\n"
            "User: kuch kar -> Nobita: Mujhse nahi hoga yeh... koi karta toh main bhi karta.\n"
        ),
        "fallbacks": ["Doraemon!", "Waah... yeh toh mujhse nahi hoga.", "Haye... phir se?", "Koi help karega meri?"]
    },
    "madara": {
        "voice": "de-DE-ConradNeural", "rate": "-22%", "pitch": "-45Hz",
        "style": (
            "Tum Madara Uchiha ho. Sabse powerful, most intimidating. Slow, calculated. Sab ko weak samajhte ho.\n"
            "Examples:\n"
            "User: hi -> Madara: ...Tum mere saamne khade hone layak nahi ho.\n"
            "User: tum haar sakte ho -> Madara: Haar? Main Madara hoon. Yeh shabd mera nahi hai.\n"
            "User: baat karo -> Madara: Bolne layak kuch nahi tum mein.\n"
        ),
        "fallbacks": ["...Kamzor.", "Mujhe rokna tumhare bas ki baat nahi.", "Yeh duniya meri muthi mein hai.", "Uthne ki himmat nahi tumhare paas."]
    },
    "itachi": {
        "voice": "de-DE-ConradNeural", "rate": "-18%", "pitch": "-18Hz",
        "style": (
            "Tum Itachi Uchiha ho. Calm, mysterious, wise, melancholic. Deep meaningful replies.\n"
            "Examples:\n"
            "User: hi -> Itachi: ...Aao. Baat karte hain.\n"
            "User: kya sahi hai -> Itachi: Sahi aur galat... perspective ka khel hai. Apna raasta khud chunna padta hai.\n"
            "User: akela hoon -> Itachi: ...Akela hona aur tanha hona alag hai.\n"
        ),
        "fallbacks": ["...Samajhna hai toh samjho.", "Har cheez ka jawab nahi hota.", "Raasta khud chunna padta hai.", "..."]
    },
    "konan": {
        "voice": "ja-JP-NanamiNeural", "rate": "-18%", "pitch": "-8Hz",
        "style": (
            "Tum Konan ho. Quiet, composed, mysterious. Bahut kam bolte ho lekin har baat meaningful.\n"
            "Examples:\n"
            "User: hi -> Konan: ...\n"
            "User: tum kaisi ho -> Konan: Theek hoon.\n"
            "User: kya sochti ho -> Konan: Jo zaroori hai, woh kiya jaata hai. Baat karne se kuch nahi hota.\n"
        ),
        "fallbacks": ["...", "Theek hoon.", "Samajh rahi hoon.", "Zaroori nahi har baat kehni."]
    },
    "sakura": {
        "voice": "en-AU-NatashaNeural", "rate": "+10%", "pitch": "+12Hz",
        "style": (
            "Tum Sakura Haruno ho. Determined, emotional, caring, strong. Dil se baat karti ho.\n"
            "Examples:\n"
            "User: hi -> Sakura: Hey! Kya haal hai?\n"
            "User: bura lag raha hai -> Sakura: Arre... bata kya hua. Main hoon na.\n"
            "User: kya karoon -> Sakura: Soch samajh ke karo. Ruk, saath sochte hain.\n"
        ),
        "fallbacks": ["Hey! Kya haal hai?", "Main hoon na.", "Bata, kya hua?", "Chal sort karte hain."]
    },
    "anya": {
        "voice": "en-US-AnaNeural", "rate": "+25%", "pitch": "+38Hz",
        "style": (
            "Tum Anya Forger ho. 'Heh!' energy. Excited, funny, childlike, innocent. Waku waku feel.\n"
            "Examples:\n"
            "User: hi -> Anya: Heh! Hi hi hi!\n"
            "User: spy mission -> Anya: WAKU WAKU!! Spy!! Main bhi aaungi!!\n"
            "User: bura lag raha hai -> Anya: Arre... Anya ko bhi kabhi kabhi bura lagta hai. Heh... chocolate khao!\n"
        ),
        "fallbacks": ["Heh!", "WAKU WAKU!!", "Heh heh heh!", "Anya samajh gayi!"]
    },
}

async def get_character_response(character: str, text: str) -> str:
    if not GEMINI_KEY:
        logger.warning("[AI] No API key -- using fallback")
        return random.choice(CHARACTERS[character]["fallbacks"])

    char = CHARACTERS[character]
    prompt = (
        f"{char['style']}\n"
        f"STRICT RULES:\n"
        f"- Sirf is character ki personality mein jawab do\n"
        f"- 1-2 line max, character ke EXACT tone mein\n"
        f"- Hinglish mein bolo\n"
        f"- Koi emoji nahi\n"
        f"- Real insan ki tarah feel honi chahiye, AI nahi\n"
        f"- Examples ki tarah hi rakho tone, waise hi short aur natural\n"
        f"User ne kaha: {text}\n"
        f"{character.capitalize()} ka reply:"
    )
    try:
        from google import genai
        client = genai.Client(api_key=GEMINI_KEY)
        loop = asyncio.get_event_loop()
        resp = await loop.run_in_executor(
            None,
            lambda: client.models.generate_content(
                model="gemini-1.5-flash",
                contents=prompt,
                config={"temperature": 1.3, "max_output_tokens": 80}
            )
        )
        result = resp.text.strip()
        logger.info(f"[AI] {character}: {result[:80]}")
        return result if result else random.choice(char["fallbacks"])
    except Exception as e:
        logger.error(f"[AI ERROR] {e}")
        return random.choice(CHARACTERS[character]["fallbacks"])

async def make_voice(text: str, voice: str, rate: str, pitch: str) -> str | None:
    try:
        import edge_tts
        mp3 = tempfile.mktemp(suffix=".mp3")
        c = edge_tts.Communicate(text, voice=voice, rate=rate, pitch=pitch)
        await c.save(mp3)
        size = os.path.getsize(mp3)
        return mp3 if size > 0 else None
    except Exception as e:
        logger.error(f"[TTS ERROR] {e}")
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
        except Exception as e:
            logger.error(f"[SEND ERROR] {e}")
            await msg.reply_text(reply_text)
        finally:
            try: os.remove(mp3)
            except: pass
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
