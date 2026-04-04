# vc_core.py
import os, io, asyncio, logging, tempfile
import speech_recognition as sr
from pydub import AudioSegment

logger = logging.getLogger(__name__)

API_ID           = int(os.getenv("API_ID", "0"))
API_HASH         = os.getenv("API_HASH", "")
BOT_TOKEN        = os.getenv("BOT_TOKEN", "")
PYROGRAM_SESSION = os.getenv("PYROGRAM_SESSION", "")

active_vc_chats: set = set()
vc_listening:    dict = {}

_assistant_session: str = ""


def add_assistant(session_string: str):
    global _assistant_session
    _assistant_session = session_string
    logger.info("[VC] Assistant session saved")


def remove_assistant():
    global _assistant_session
    _assistant_session = ""
    logger.info("[VC] Assistant session removed")


def make_tts_wav(text: str, out_path: str = None) -> str:
    if not out_path:
        out_path = tempfile.mktemp(suffix=".wav")
    try:
        import edge_tts
        mp3_path = tempfile.mktemp(suffix=".mp3")

        async def _gen():
            c = edge_tts.Communicate(text, voice="hi-IN-SwaraNeural",
                                     rate="+8%", pitch="+15Hz")
            await c.save(mp3_path)

        loop = asyncio.new_event_loop()
        loop.run_until_complete(_gen())
        loop.close()
        audio = AudioSegment.from_mp3(mp3_path)
        audio = audio.set_channels(1).set_frame_rate(48000)
        audio.export(out_path, format="wav")
        try:
            os.remove(mp3_path)
        except:
            pass
        return out_path
    except Exception as e:
        logger.error(f"[TTS WAV] {e}")
        return ""


def make_tts_ogg(text: str) -> bytes:
    try:
        import edge_tts
        mp3_path = tempfile.mktemp(suffix=".mp3")

        async def _gen():
            c = edge_tts.Communicate(text, voice="hi-IN-SwaraNeural",
                                     rate="+8%", pitch="+15Hz")
            await c.save(mp3_path)

        loop = asyncio.new_event_loop()
        loop.run_until_complete(_gen())
        loop.close()
        audio = AudioSegment.from_mp3(mp3_path)
        buf = io.BytesIO()
        audio.export(buf, format="ogg", codec="libopus", bitrate="64k")
        buf.seek(0)
        try:
            os.remove(mp3_path)
        except:
            pass
        return buf.read()
    except Exception as e:
        logger.error(f"[TTS OGG] {e}")
        return b""


def stt_from_bytes(audio_bytes: bytes) -> str:
    try:
        seg = AudioSegment.from_file(io.BytesIO(audio_bytes), format="ogg")
        wav_io = io.BytesIO()
        seg.export(wav_io, format="wav")
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


async def join_vc(chat_id: int, bot_app=None, ai_func=None) -> bool:
    logger.warning("[VC] pytgcalls not installed -- VC disabled")
    return False


async def leave_vc(chat_id: int) -> bool:
    active_vc_chats.discard(chat_id)
    return False


async def speak_in_vc(chat_id: int, text: str) -> bool:
    return False


async def start_vc_system():
    logger.info("[VC] VC system skipped")


async def stop_vc_system():
    pass
