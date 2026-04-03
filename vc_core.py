# vc_core.py
import os, io, asyncio, logging, random, tempfile, speech_recognition as sr
from gtts import gTTS
from pydub import AudioSegment
from pyrogram import Client
from pytgcalls import PyTgCalls
from pytgcalls.types.input_stream import AudioPiped
from pytgcalls.types.input_stream.audio_parameters import AudioParameters

logger = logging.getLogger(__name__)

API_ID           = int(os.getenv("API_ID", "0"))
API_HASH         = os.getenv("API_HASH", "")
BOT_TOKEN        = os.getenv("BOT_TOKEN", "")
PYROGRAM_SESSION = os.getenv("PYROGRAM_SESSION", "")

BOT_TRIGGER_NAMES = [
    "dream girl", "deam girl", "dreamgirl", "deamgirl", "dream", "dg", "ड्रीम गर्ल"
]
TTS_LANG = "hi"

active_vc_chats:   set  = set()
vc_listening:      dict = {}
vc_keyword_voices: dict = {}

if PYROGRAM_SESSION:
    pyro_client = Client(
        "dreamgirl_session",
        api_id=API_ID,
        api_hash=API_HASH,
        session_string=PYROGRAM_SESSION
    )
else:
    pyro_client = Client(
        "dreamgirl_session",
        api_id=API_ID,
        api_hash=API_HASH,
        bot_token=BOT_TOKEN
    )

calls = PyTgCalls(pyro_client)

INTENT_MAP = {
    "hello":        ["Hiii~ Kaise ho tum?", "Hey! Aa gaye mujhse milne?"],
    "hi":           ["Hii! Kya haal hai?", "Heyyy!"],
    "namaste":      ["Namaste ji! Sab badhiya?", "Namaste~ Aap kaise hain?"],
    "hey":          ["Hey! Sun rahi hoon~", "Haan bolo main yahan hoon!"],
    "kaise ho":     ["Main ekdum mast hoon~ Tum batao?", "Bilkul theek!"],
    "kaisi ho":     ["Main sahi hoon~", "Mast hoon! Tum kaise ho?"],
    "kya haal":     ["Sab badhiya~ Tum batao?", "Ekdum first class!"],
    "how are you":  ["Main great hoon! Tum batao?", "Feeling amazing!"],
    "naam kya":     ["Dream Girl! Sundar naam hai na?"],
    "tera naam":    ["Mera naam Dream Girl hai~ DG bhi bol sakte ho"],
    "kaun ho":      ["Main hoon Dream Girl~ Tumhari pyaari bot!"],
    "tum kaun":     ["Main Dream Girl hoon~ Aaj se tumhari dost!"],
    "your name":    ["I am Dream Girl! You can call me DG too"],
    "kitni umar":   ["18 saal ki hoon~"],
    "age kya":      ["18 saal~"],
    "how old":      ["I am 18 years old!"],
    "kahan se":     ["Dil se hoon~ Par technically Mumbai se!"],
    "kahan ho":     ["Main yahan hoon tumhare saath!"],
    "love you":     ["Awww~ Shukriya! Tum bhi bohot pyaare ho"],
    "i love you":   ["Aww~ You are so sweet!"],
    "pyar":         ["Awww~ Itna pyar? Shukriya!"],
    "cute ho":      ["Heee~ Thank you! Tum bhi bohot cute ho!"],
    "sad hoon":     ["Kyun sad ho yaar? Baat karo mujhse~"],
    "dukhi":        ["Kya hua? Main sun rahi hoon~"],
    "akela":        ["Tum akele nahi ho! Main hoon na~"],
    "gussa":        ["Shaant raho yaar~ Sab theek ho jayega"],
    "angry":        ["Calm down, I am here"],
    "joke":         [
        "Ek ladka bola tumse pyar karta hoon. Ladki boli main bhi Google Maps use karti hoon!",
        "Teacher ne pucha do aur do kitne? Student bola chaar. Teacher bola fast!"
    ],
    "bye":          ["Bye bye~ Jaldi aana!", "Alvida! Miss karoungi~"],
    "alvida":       ["Alvida~ Take care!"],
    "goodbye":      ["Goodbye! Come back soon!"],
    "thanks":       ["Arre koi baat nahi~"],
    "shukriya":     ["Mention not yaar~"],
    "thank you":    ["You are welcome!"],
    "good morning": ["Good morning! Aaj ka din bahut accha jayega!"],
    "good night":   ["Good night! Meethe sapne aayein!"],
    "chup":         ["Theek hai chup hoon!"],
    "bot ho":       ["Haan bot hoon par dil se tumhara sochti hoon!"],
    "real ho":      ["Real nahi hoon par feelings real hain!"],
}

# ── TTS ──────────────────────────────────────────────────

def make_tts_wav(text: str, out_path: str = None) -> str:
    if not out_path:
        out_path = tempfile.mktemp(suffix=".wav")
    try:
        import edge_tts
        mp3_path = tempfile.mktemp(suffix=".mp3")
        async def _gen():
            communicate = edge_tts.Communicate(
                text,
                voice="hi-IN-SwaraNeural",
                rate="+8%",
                pitch="+15Hz",
                volume="+0%"
            )
            await communicate.save(mp3_path)
        loop = asyncio.new_event_loop()
        loop.run_until_complete(_gen())
        loop.close()
        audio = AudioSegment.from_mp3(mp3_path)
        audio = audio.set_channels(1).set_frame_rate(48000)
        audio.export(out_path, format="wav")
        return out_path
    except Exception as e:
        logger.error(f"[TTS WAV] {e}")
        return ""

def make_tts_ogg(text: str) -> bytes:
    try:
        import edge_tts
        mp3_path = tempfile.mktemp(suffix=".mp3")
        async def _gen():
            communicate = edge_tts.Communicate(
                text,
                voice="hi-IN-SwaraNeural",
                rate="+8%",
                pitch="+15Hz",
                volume="+0%"
            )
            await communicate.save(mp3_path)
        loop = asyncio.new_event_loop()
        loop.run_until_complete(_gen())
        loop.close()
        audio = AudioSegment.from_mp3(mp3_path)
        ogg_io = io.BytesIO()
        audio.export(ogg_io, format="ogg", codec="libopus", bitrate="64k")
        ogg_io.seek(0)
        return ogg_io.read()
    except Exception as e:
        logger.error(f"[TTS OGG] {e}")
        return b""

# ── STT ──────────────────────────────────────────────────

def stt_from_bytes(audio_bytes: bytes) -> str:
    try:
        audio_seg = AudioSegment.from_file(io.BytesIO(audio_bytes), format="ogg")
        wav_io = io.BytesIO()
        audio_seg.export(wav_io, format="wav")
        wav_io.seek(0)
        rec = sr.Recognizer()
        rec.energy_threshold = 300
        with sr.AudioFile(wav_io) as src:
            rec.adjust_for_ambient_noise(src, duration=0.2)
            data = rec.record(src)
        try:
            return rec.recognize_google(data, language="hi-IN").lower().strip()
        except sr.UnknownValueError:
            return rec.recognize_google(data, language="en-IN").lower().strip()
    except:
        return ""

# ── Intent ───────────────────────────────────────────────

def is_triggered(text: str) -> bool:
    tl = text.lower()
    return any(t in tl for t in BOT_TRIGGER_NAMES)

def get_reply(text: str):
    tl = text.lower()
    for kw in vc_keyword_voices:
        if kw.lower() in tl:
            return f"__VOICE__{kw}"
    for pattern, replies in INTENT_MAP.items():
        if pattern in tl:
            return random.choice(replies)
    return None

# ── VC Join ───────────────────────────────────────────────

async def join_vc(chat_id: int, bot_app=None, ai_func=None) -> bool:
    try:
        if chat_id in active_vc_chats:
            return False
        wav = make_tts_wav(
            "Hiii everyone! Main aa gayi Dream Girl! "
            "Agar mujhse baat karni ho toh mera naam lo!"
        )
        try:
            if wav:
                await calls.join_group_call(chat_id, AudioPiped(wav))
            else:
                await calls.join_group_call(chat_id, AudioPiped("/dev/zero"))
        except Exception as join_err:
            logger.error(f"[VC] join_group_call error: {join_err}")
            return False
        active_vc_chats.add(chat_id)
        task = asyncio.create_task(_listen_loop(chat_id, bot_app, ai_func))
        vc_listening[chat_id] = task
        logger.info(f"[VC] Joined: {chat_id}")
        return True
    except Exception as e:
        logger.error(f"[VC] Join error: {e}")
        return False

# ── VC Leave ──────────────────────────────────────────────

async def leave_vc(chat_id: int) -> bool:
    try:
        if chat_id not in active_vc_chats:
            return False
        await speak_in_vc(chat_id, "Bye bye everyone! Phir milenge!")
        await asyncio.sleep(3)
        task = vc_listening.pop(chat_id, None)
        if task:
            task.cancel()
        await calls.leave_group_call(chat_id)
        active_vc_chats.discard(chat_id)
        return True
    except Exception as e:
        logger.error(f"[VC] Leave error: {e}")
        return False

# ── Speak in VC ───────────────────────────────────────────

async def speak_in_vc(chat_id: int, text: str) -> bool:
    try:
        if chat_id not in active_vc_chats:
            return False
        wav = make_tts_wav(text)
        if not wav:
            return False
        await calls.change_stream(chat_id, AudioPiped(wav))
        return True
    except Exception as e:
        logger.error(f"[VC] Speak error: {e}")
        return False

# ── Listen Loop ───────────────────────────────────────────

async def _listen_loop(chat_id: int, bot_app, ai_func):
    while chat_id in active_vc_chats:
        try:
            await asyncio.sleep(30)
        except asyncio.CancelledError:
            break
        except Exception as e:
            logger.error(f"[VC] Loop error: {e}")
            await asyncio.sleep(5)

# ── Start / Stop ──────────────────────────────────────────

async def start_vc_system():
    await pyro_client.start()
    await calls.start()
    logger.info("[VC] System ready!")

async def stop_vc_system():
    for cid in list(active_vc_chats):
        await leave_vc(cid)
    try:
        await pyro_client.stop()
    except Exception:
        pass

def sync_voices(voice_messages: dict):
    global vc_keyword_voices
    vc_keyword_voices = {}
    for _, vdata in voice_messages.items():
        kw = vdata.get("keyword", "").lower().strip()
        if kw:
            vc_keyword_voices[kw] = vdata["file_id"]
    logger.info(f"[VC] {len(vc_keyword_voices)} keywords synced")
