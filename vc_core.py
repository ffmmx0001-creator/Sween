# vc_core.py
import os, io, asyncio, logging, tempfile
import speech_recognition as sr
from pydub import AudioSegment

logger = logging.getLogger(__name__)

API_ID           = int(os.getenv("API_ID", "0"))
API_HASH         = os.getenv("API_HASH", "")
BOT_TOKEN        = os.getenv("BOT_TOKEN", "")

active_vc_chats: set = set()
vc_listening:    dict = {}

_assistant_session: str = ""
_assistant_client = None
_assistant_calls  = None


def add_assistant(session_string: str):
    global _assistant_session
    _assistant_session = session_string.strip()
    logger.info("[VC] Assistant session saved")


def remove_assistant():
    global _assistant_session, _assistant_client, _assistant_calls
    _assistant_session = ""
    _assistant_client  = None
    _assistant_calls   = None
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


async def _get_or_create_calls():
    global _assistant_client, _assistant_calls
    if not _assistant_session:
        return None
    if _assistant_calls is not None:
        return _assistant_calls
    try:
        from pyrogram import Client
        from pytgcalls import PyTgCalls
        _assistant_client = Client(
            "assistant_vc",
            api_id=API_ID,
            api_hash=API_HASH,
            session_string=_assistant_session
        )
        _assistant_calls = PyTgCalls(_assistant_client)
        await _assistant_client.start()
        await _assistant_calls.start()
        logger.info("[VC] Assistant client started")
        return _assistant_calls
    except Exception as e:
        logger.error(f"[VC] Assistant start error: {e}")
        return None


async def join_vc(chat_id: int, bot_app=None, ai_func=None) -> bool:
    try:
        calls = await _get_or_create_calls()
        if calls is None:
            logger.error("[VC] No assistant session. Use /addasis first.")
            return False
        if chat_id in active_vc_chats:
            return False
        from pytgcalls.types import AudioPiped
        wav = make_tts_wav(
            "Hiii everyone! Main aa gayi Dream Girl! "
            "Agar mujhse baat karni ho toh mera naam lo!"
        )
        try:
            if wav and os.path.exists(wav):
                await calls.join_group_call(chat_id, AudioPiped(wav))
            else:
                await calls.join_group_call(chat_id, AudioPiped("/dev/zero"))
        except Exception as je:
            logger.error(f"[VC] join_group_call: {je}")
            return False
        active_vc_chats.add(chat_id)
        task = asyncio.create_task(_listen_loop(chat_id, bot_app, ai_func))
        vc_listening[chat_id] = task
        logger.info(f"[VC] Joined: {chat_id}")
        return True
    except Exception as e:
        logger.error(f"[VC] Join error: {e}")
        return False


async def leave_vc(chat_id: int) -> bool:
    try:
        if chat_id not in active_vc_chats:
            return False
        await speak_in_vc(chat_id, "Bye bye everyone! Phir milenge!")
        await asyncio.sleep(2)
        task = vc_listening.pop(chat_id, None)
        if task:
            task.cancel()
        if _assistant_calls:
            await _assistant_calls.leave_group_call(chat_id)
        active_vc_chats.discard(chat_id)
        return True
    except Exception as e:
        logger.error(f"[VC] Leave error: {e}")
        active_vc_chats.discard(chat_id)
        return False


async def speak_in_vc(chat_id: int, text: str) -> bool:
    try:
        if chat_id not in active_vc_chats or _assistant_calls is None:
            return False
        from pytgcalls.types import AudioPiped
        wav = make_tts_wav(text)
        if not wav:
            return False
        await _assistant_calls.change_stream(chat_id, AudioPiped(wav))
        return True
    except Exception as e:
        logger.error(f"[VC] Speak error: {e}")
        return False


async def _listen_loop(chat_id: int, bot_app, ai_func):
    while chat_id in active_vc_chats:
        try:
            await asyncio.sleep(30)
        except asyncio.CancelledError:
            break
        except Exception as e:
            logger.error(f"[VC] Loop error: {e}")
            await asyncio.sleep(5)


async def start_vc_system():
    logger.info("[VC] VC system ready. Use /addasis to set assistant session.")


async def stop_vc_system():
    for cid in list(active_vc_chats):
        await leave_vc(cid)
    global _assistant_client
    if _assistant_client:
        try:
            await _assistant_client.stop()
        except:
            pass
