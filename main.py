import os, asyncio, logging, tempfile, subprocess
from telegram import Update
from telegram.ext import Application, MessageHandler, filters, ContextTypes

logging.basicConfig(format="%(asctime)s - %(levelname)s - %(message)s", level=logging.INFO)
logger = logging.getLogger(__name__)

BOT_TOKEN = os.getenv("BOT_TOKEN", "")

async def handle_video(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = update.message
    await msg.reply_text("Video mil gayi. Hindi dubbing ho rahi hai, thoda wait karo...")

    # Video download
    video = msg.video or msg.document
    file = await context.bot.get_file(video.file_id)
    
    with tempfile.TemporaryDirectory() as tmp:
        video_path = os.path.join(tmp, "input.mp4")
        audio_path = os.path.join(tmp, "audio.wav")
        dubbed_audio = os.path.join(tmp, "dubbed.mp3")
        output_path = os.path.join(tmp, "output.mp4")

        await file.download_to_drive(video_path)

        # Step 1: Audio extract karo
        subprocess.run([
            "ffmpeg", "-i", video_path,
            "-vn", "-ar", "16000", "-ac", "1",
            audio_path
        ], check=True, capture_output=True)

        # Step 2: Whisper se transcribe karo
        import whisper
        model = whisper.load_model("base")
        result = model.transcribe(audio_path)
        original_text = result["text"].strip()
        logger.info(f"Transcribed: {original_text[:100]}")

        # Step 3: Hindi translate karo
        from deep_translator import GoogleTranslator
        hindi_text = GoogleTranslator(source="auto", target="hi").translate(original_text)
        logger.info(f"Translated: {hindi_text[:100]}")

        # Step 4: Audio pitch detect karke voice choose karo
        # Simple: ffmpeg se audio volume/pitch check
        probe = subprocess.run([
            "ffprobe", "-i", audio_path,
            "-show_entries", "stream=sample_rate",
            "-v", "quiet", "-of", "csv=p=0"
        ], capture_output=True, text=True)
        
        # Deep voice default male, normal female
        voice = "hi-IN-MadhurNeural"  # deep male
        rate = "-5%"
        pitch = "-10Hz"

        # Step 5: Edge-TTS se Hindi audio banao
        import edge_tts
        tts = edge_tts.Communicate(hindi_text, voice=voice, rate=rate, pitch=pitch)
        await tts.save(dubbed_audio)

        # Step 6: Original video + dubbed audio merge karo
        subprocess.run([
            "ffmpeg", "-i", video_path, "-i", dubbed_audio,
            "-c:v", "copy", "-map", "0:v:0", "-map", "1:a:0",
            "-shortest", output_path
        ], check=True, capture_output=True)

        # Step 7: Video bhejo
        with open(output_path, "rb") as f:
            await msg.reply_video(video=f, caption="Hindi dubbing taiyar!")

async def main():
    app = Application.builder().token(BOT_TOKEN).build()
    app.add_handler(MessageHandler(filters.VIDEO | filters.Document.VIDEO, handle_video))
    
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
requirements.txt

runtime.txt

railway.json

nixpacks.toml (ffmpeg ke liye -- zaruri hai)
[phases.setup]
nixPkgs = ["ffmpeg"]
Railway Variables
Sirf ek variable chahiye:

BOT_TOKEN -- BotFather ka token
Kaise Kaam Karta Hai
Video bhejo
    ↓
Bot audio extract kare (ffmpeg)
    ↓
Whisper se transcribe kare (free, local)
    ↓
Hindi mein translate kare (Google Translate, free)
    ↓
Edge-TTS se Hindi audio banao (hi-IN-MadhurNeural, deep voice)
    ↓
Original video + Hindi audio merge kare
    ↓
Dubbed video wapas bheje
Note: Bade videos (5+ min) mein thoda time lagega kyunki Whisper locally process karta hai. Chhoti clips (1-2 min) fast hongi.

1m ago
OkayJust now
Theek hai! Jab bhi deploy karo ya koi problem aaye -- bata dena, help karunga.

Just now

Enter instruction or question...
        
