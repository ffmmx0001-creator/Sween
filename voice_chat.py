# voice_chat.py
import io, logging, speech_recognition as sr
from pydub import AudioSegment
from vc_core import make_tts_ogg, get_reply, is_triggered, vc_keyword_voices

logger = logging.getLogger(__name__)

async def handle_voice_message(update, context, settings, ai_func):
    msg  = update.message
    user = update.effective_user
    if not msg or not msg.voice:
        return
    try:
        vf          = await context.bot.get_file(msg.voice.file_id)
        audio_bytes = bytes(await vf.download_as_bytearray())
        recognized  = _stt(audio_bytes)

        if not recognized:
            ogg = make_tts_ogg("Kuch samajh nahi aaya~ Dobara bolna please?")
            if ogg:
                ogg_io = io.BytesIO(ogg); ogg_io.name = "r.ogg"
                await msg.reply_voice(voice=ogg_io)
            return

        chat_type = update.effective_chat.type
        if chat_type in ("group", "supergroup") and not is_triggered(recognized):
            return

        reply_text = get_reply(recognized)

        if reply_text and reply_text.startswith("__VOICE__"):
            kw  = reply_text.replace("__VOICE__", "")
            fid = vc_keyword_voices.get(kw)
            if fid:
                await msg.reply_voice(voice=fid)
            return

        if not reply_text:
            display    = user.first_name or "Pyaare"
            reply_text = await ai_func(recognized, display, user.id)

        ogg_bytes = make_tts_ogg(reply_text)
        if ogg_bytes:
            ogg_io      = io.BytesIO(ogg_bytes); ogg_io.name = "dg.ogg"
            await msg.reply_voice(voice=ogg_io, caption=f"🌸 _{reply_text}_", parse_mode="Markdown")
        else:
            await msg.reply_text(f"🌸 {reply_text}")
    except Exception as e:
        logger.error(f"[VoiceMsg] {e}")

def _stt(audio_bytes: bytes) -> str:
    try:
        audio = AudioSegment.from_file(io.BytesIO(audio_bytes), format="ogg")
        wav   = io.BytesIO()
        audio.export(wav, format="wav")
        wav.seek(0)
        rec = sr.Recognizer()
        rec.energy_threshold = 300
        rec.dynamic_energy_threshold = True
        with sr.AudioFile(wav) as src:
            rec.adjust_for_ambient_noise(src, duration=0.2)
            data = rec.record(src)
        try:
            return rec.recognize_google(data, language="hi-IN").lower().strip()
        except sr.UnknownValueError:
            return rec.recognize_google(data, language="en-IN").lower().strip()
    except:
        return ""
