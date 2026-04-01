import os, json, random, asyncio, io
from datetime import datetime, timedelta
from collections import defaultdict
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, ContextTypes
import google.generativeai as genai

BOT_TOKEN = os.environ.get("BOT_TOKEN", "")
ADMIN_ID = int(os.environ.get("ADMIN_ID", "0"))
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "")

users_started = set()
groups = set()
chat_enabled = defaultdict(lambda: True)
clones = {}
reply_counts = defaultdict(lambda: defaultdict(lambda: defaultdict(int)))
recent_group_users = defaultdict(set)
gfbf_data = {}
bff_data = {}

settings = {
    "photo_list": [],
    "photo_counter": 0,
    "start_caption": None,
    "start_buttons": {
        "GROUP": "https://t.me/+ro9WnBB5U2kwMDJl",
        "OWNER": "https://t.me/OwnerSween",
        "CHANNEL": "https://t.me/SweenSpy",
        "KIDNAP": "https://t.me/SweenSpyBoT?start=_tgr_SAH_2gg5ZTc9",
        "GAME": "https://t.me/SINZHU_WAIFU_BOT?start=_tgr_VdCgVxg1ZjNl",
    },
    "custom_replies": {},
    "voice_messages": {},
    "voice_counter": 0,
    "status_caption": "🗿Total Users : {users}\n🌐 Total Groups : {groups}",
    "photo_captions": [],
    "caption_counter": 0,
}

DATA_FILE = "data.json"

def load_data():
    global users_started, groups
    try:
        with open(DATA_FILE) as f:
            d = json.load(f)
            users_started = set(d.get("users", []))
            groups = set(d.get("groups", []))
            loaded = d.get("settings", {})
            for k, v in loaded.items():
                settings[k] = v
            # migrate old single start_photo
            if settings.get("start_photo") and not settings.get("photo_list"):
                settings["photo_counter"] = 1
                settings["photo_list"] = [{"id": 1, "file_id": settings["start_photo"]}]
            for key in ["voice_messages","photo_list","photo_captions","custom_replies"]:
                if key not in settings:
                    settings[key] = {} if key == "voice_messages" else []
            for key in ["voice_counter","photo_counter","caption_counter"]:
                if key not in settings:
                    settings[key] = 0
            if "status_caption" not in settings:
                settings["status_caption"] = "🗿Total Users : {users}\n🌐 Total Groups : {groups}"
    except:
        pass

def save_data():
    with open(DATA_FILE, "w") as f:
        json.dump({"users": list(users_started), "groups": list(groups), "settings": settings}, f)

genai.configure(api_key=GEMINI_API_KEY)
model = genai.GenerativeModel('gemini-1.5-flash')

SYSTEM_PROMPT = """Tu ek 16 saal ki Bengali ladki hai jiska naam Sinzhu hai. Tu West Bengal ke Kolkata se hai. Tu abhi Class 10th mein padhti hai. Tu bahut friendly hai aur sabse girlfriend jaise baat karti hai. Tu Hinglish (Hindi + English mix) mein baat karti hai - natural aur casual style mein. Tu emoji use karti hai. Tu real insaan ki tarah baat karti hai, AI nahi. Chhoti aur natural replies dena."""

async def get_ai_response(message: str, display_name: str = "") -> str:
    try:
        prompt = f"{SYSTEM_PROMPT}\n\n{display_name} ne kaha: {message}\n\nSinzhu ka reply ({display_name} ko address karo):"
        response = model.generate_content(prompt)
        return response.text
    except:
        return random.choice(["hehe 😄", "arrey wah! 😊", "haan bolo bolo 👀", "sach mein? 😮", "OMG really? 😱", "lol kya baat hai 😂"])

def get_custom_reply(text: str):
    text_lower = text.lower()
    for keyword, reply in settings["custom_replies"].items():
        if keyword.lower() in text_lower:
            return reply
    return None

def get_voice_for_text(text: str):
    text_lower = text.lower()
    matches = []
    for vdata in settings["voice_messages"].values():
        kw = vdata.get("keyword", "")
        if kw and kw.lower() in text_lower:
            matches.append(vdata["file_id"])
    return random.choice(matches) if matches else None

def get_welcome_keyboard():
    b = settings["start_buttons"]
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🀄 GROUP", url=b.get("GROUP","#")), InlineKeyboardButton("⚽ OWNER", url=b.get("OWNER","#"))],
        [InlineKeyboardButton("🦋 CHANNEL", url=b.get("CHANNEL","#")), InlineKeyboardButton("💖 GAME", url=b.get("GAME","#"))],
        [InlineKeyboardButton("💖 ᴋɪᴅɴᴀᴘ ᴋᴀʀʟᴏ 💫", url=b.get("KIDNAP","#"))],
    ])

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    chat = update.effective_chat
    users_started.add(user.id)
    if chat.type in ["group", "supergroup"]:
        groups.add(chat.id)
    save_data()
    mention = f"[{user.first_name}](tg://user?id={user.id})"
    welcome = f"*😋 Hɪᴇᴇᴇᴇᴇ {mention}*\n😉 Yᴏᴜ'ʀᴇ Tᴀʟᴋɪɴɢ Tᴏ\nA Cᴜᴛɪᴇ Bacchi\n\n💕 Cʜᴏᴏsᴇ Aɴ Oᴘᴛɪᴏɴ Bᴇʟᴏᴡ :"
    caption = settings.get("start_caption") or welcome
    photos = settings.get("photo_list", [])
    kb = get_welcome_keyboard()
    if photos:
        photo = random.choice(photos)
        await update.message.reply_photo(photo=photo["file_id"], caption=caption, parse_mode="Markdown", reply_markup=kb)
    else:
        await update.message.reply_text(welcome, parse_mode="Markdown", reply_markup=kb)

async def setphoto_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        return
    msg = update.message
    reply = msg.reply_to_message
    if not reply or not reply.photo:
        await msg.reply_text("❌ Kisi photo ki reply mein /setphoto ya /addphoto likho!")
        return
    file_id = reply.photo[-1].file_id
    settings["photo_counter"] = settings.get("photo_counter", 0) + 1
    pid = settings["photo_counter"]
    settings["photo_list"].append({"id": pid, "file_id": file_id})
    save_data()
    await msg.reply_text(f"✅ Start photo add ho gayi!\n🆔 ID: `{pid}` | Total: {len(settings['photo_list'])}", parse_mode="Markdown")

async def photolist_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        return
    photos = settings.get("photo_list", [])
    if not photos:
        await update.message.reply_text("Koi start photo save nahi hai.")
        return
    text = "📸 *Start Photos List:*\n\n"
    for p in photos:
        text += f"🆔 ID: `{p['id']}`\n"
    text += f"\n*Total:* {len(photos)}"
    await update.message.reply_text(text, parse_mode="Markdown")

async def resetpic_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        return
    if context.args:
        try:
            pid = int(context.args[0])
            before = len(settings["photo_list"])
            settings["photo_list"] = [p for p in settings["photo_list"] if p["id"] != pid]
            if len(settings["photo_list"]) < before:
                save_data()
                await update.message.reply_text(f"✅ Photo ID `{pid}` hata diya!", parse_mode="Markdown")
            else:
                await update.message.reply_text(f"❌ Photo ID `{pid}` nahi mila.", parse_mode="Markdown")
        except:
            await update.message.reply_text("Usage: /resetpic <id>")
    else:
        settings["photo_list"] = []
        save_data()
        await update.message.reply_text("✅ Saari start photos hata di!")

async def chaton(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat = update.effective_chat
    user = update.effective_user
    try:
        member = await chat.get_member(user.id)
        if member.status in ["administrator", "creator"] or user.id == ADMIN_ID:
            chat_enabled[chat.id] = True
            await update.message.reply_text("✅ Chat ON! 😊")
    except:
        pass

async def chatoff(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat = update.effective_chat
    user = update.effective_user
    try:
        member = await chat.get_member(user.id)
        if member.status in ["administrator", "creator"] or user.id == ADMIN_ID:
            chat_enabled[chat.id] = False
            await update.message.reply_text("😴 Thodi so leti hoon... /CHATON se jagana!")
    except:
        pass

async def broadcast(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        await update.message.reply_text("Sirf admin ke liye!")
        return
    msg = update.message
    sent = failed = 0
    for cid in list(users_started) + list(groups):
        try:
            if msg.reply_to_message:
                await msg.reply_to_message.copy(chat_id=cid)
            elif context.args:
                await context.bot.send_message(cid, " ".join(context.args))
            sent += 1
        except:
            failed += 1
        await asyncio.sleep(0.05)
    await msg.reply_text(f"✅ Broadcast done!\nSent: {sent} | Failed: {failed}")

async def clone_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        await update.message.reply_text("Sirf admin ke liye!")
        return
    if not context.args:
        await update.message.reply_text("Usage: /clone <bot_token>")
        return
    token = context.args[0]
    if token in clones:
        await update.message.reply_text("Yeh bot pehle se clone hai!")
        return
    try:
        clone_app = ApplicationBuilder().token(token).build()
        add_handlers(clone_app)
        await clone_app.initialize()
        await clone_app.start()
        asyncio.create_task(clone_app.updater.start_polling(drop_pending_updates=True))
        clones[token] = {"app": clone_app, "owner": update.effective_user.id}
        await update.message.reply_text(f"✅ Clone ho gaya! Token: `{token[:15]}...`", parse_mode="Markdown")
    except Exception as e:
        await update.message.reply_text(f"❌ Clone failed: {str(e)[:200]}")

async def dclone_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        await update.message.reply_text("Sirf admin ke liye!")
        return
    to_remove = [t for t, d in clones.items() if d["owner"] == update.effective_user.id]
    for token in to_remove:
        try:
            app = clones[token]["app"]
            await app.updater.stop()
            await app.stop()
            await app.shutdown()
        except:
            pass
        clones.pop(token, None)
    await update.message.reply_text(f"✅ {len(to_remove)} clone(s) hata diye!")

async def bbcast(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        await update.message.reply_text("Sirf admin ke liye!")
        return
    msg = update.message
    sent = 0
    for token, data in clones.items():
        capp = data["app"]
        for uid in users_started:
            try:
                if msg.reply_to_message:
                    await msg.reply_to_message.copy(chat_id=uid)
                else:
                    await capp.bot.send_message(uid, " ".join(context.args) if context.args else "Hello!")
                sent += 1
            except:
                pass
            await asyncio.sleep(0.05)
    await msg.reply_text(f"✅ Admin bcast done via {len(clones)} clones! ~{sent} messages")

async def setreply(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        return
    msg = update.message
    if msg.reply_to_message and msg.reply_to_message.text and context.args:
        keyword = msg.reply_to_message.text.strip()
        reply_text = " ".join(context.args)
        settings["custom_replies"][keyword] = reply_text
        save_data()
        await msg.reply_text(f"✅ Reply set!\n*Keyword:* `{keyword[:50]}`\n*Reply:* {reply_text}", parse_mode="Markdown")
    elif context.args and "|" in " ".join(context.args):
        parts = " ".join(context.args).split("|", 1)
        keyword, reply_text = parts[0].strip(), parts[1].strip()
        settings["custom_replies"][keyword] = reply_text
        save_data()
        await msg.reply_text(f"✅ Reply set!\n*Keyword:* `{keyword}`\n*Reply:* {reply_text}", parse_mode="Markdown")
    else:
        await msg.reply_text("2 tarike:\n1. Kisi message ki reply mein: `/setreply jawab`\n2. Direct: `/setreply keyword | jawab`", parse_mode="Markdown")

async def delreply(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        return
    if not context.args:
        await update.message.reply_text("Usage: /delreply <keyword>")
        return
    keyword = " ".join(context.args)
    if keyword in settings["custom_replies"]:
        del settings["custom_replies"][keyword]
        save_data()
        await update.message.reply_text(f"✅ Reply delete: `{keyword}`", parse_mode="Markdown")
    else:
        await update.message.reply_text(f"❌ Keyword nahi mila: `{keyword}`", parse_mode="Markdown")

async def listreplies(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        return
    if not settings["custom_replies"]:
        await update.message.reply_text("Koi custom reply set nahi hai.")
        return
    text = "📋 *Custom Replies:*\n\n"
    for kw, rep in settings["custom_replies"].items():
        text += f"🔑 `{kw[:30]}` → {rep[:50]}\n"
    await update.message.reply_text(text, parse_mode="Markdown")

async def uploadvoice_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        return
    msg = update.message
    if not msg.reply_to_message:
        await msg.reply_text("❌ Kisi voice/audio ki reply mein /uploadVoice <keyword> likho!")
        return
    reply = msg.reply_to_message
    file_id = None
    if reply.voice:
        file_id = reply.voice.file_id
    elif reply.audio:
        file_id = reply.audio.file_id
    if not file_id:
        await msg.reply_text("❌ Reply mein voice ya audio hona chahiye!")
        return
    if not context.args:
        await msg.reply_text("❌ Keyword bhi likhо: /uploadVoice hello")
        return
    keyword = " ".join(context.args)
    settings["voice_counter"] = settings.get("voice_counter", 0) + 1
    vid = str(settings["voice_counter"])
    settings["voice_messages"][vid] = {"file_id": file_id, "keyword": keyword}
    save_data()
    await msg.reply_text(f"✅ Voice upload!\n🆔 ID: `{vid}` | Keyword: `{keyword}`", parse_mode="Markdown")

async def revoice_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        return
    if not context.args:
        await update.message.reply_text("Usage: /revoice <id>")
        return
    vid = context.args[0]
    if vid in settings.get("voice_messages", {}):
        del settings["voice_messages"][vid]
        save_data()
        await update.message.reply_text(f"✅ Voice ID `{vid}` delete ho gaya!", parse_mode="Markdown")
    else:
        await update.message.reply_text(f"❌ Voice ID `{vid}` nahi mila.", parse_mode="Markdown")

async def voicelist_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        return
    voices = settings.get("voice_messages", {})
    if not voices:
        await update.message.reply_text("Koi voice upload nahi hai.")
        return
    text = "🎙️ *Uploaded Voices:*\n\n"
    for vid, vdata in voices.items():
        text += f"🆔 ID: `{vid}` | Keyword: `{vdata.get('keyword','N/A')}`\n"
    await update.message.reply_text(text, parse_mode="Markdown")

async def status_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        return
    template = settings.get("status_caption", "🗿Total Users : {users}\n🌐 Total Groups : {groups}")
    caption = template.format(users=len(users_started), groups=len(groups))
    photos = settings.get("photo_list", [])
    if photos:
        photo = random.choice(photos)
        await update.message.reply_photo(photo=photo["file_id"], caption=caption)
    else:
        await update.message.reply_text(caption)

async def setstatus_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        return
    if context.args:
        settings["status_caption"] = " ".join(context.args)
        save_data()
        await update.message.reply_text("✅ Status caption set!\nTip: `{users}` aur `{groups}` use karo count ke liye.", parse_mode="Markdown")
    else:
        await update.message.reply_text("Usage: /setstatus caption\nExample: /setstatus 🗿Users: {users} | 🌐Groups: {groups}")

async def userlist_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        return
    text = f"Total Users: {len(users_started)}\n\n" + "\n".join(str(u) for u in users_started)
    f = io.BytesIO(text.encode())
    f.name = "userlist.txt"
    await update.message.reply_document(document=f, caption=f"👥 Total Users: {len(users_started)}")

async def grouplist_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        return
    text = f"Total Groups: {len(groups)}\n\n" + "\n".join(str(g) for g in groups)
    f = io.BytesIO(text.encode())
    f.name = "grouplist.txt"
    await update.message.reply_document(document=f, caption=f"🌐 Total Groups: {len(groups)}")

async def photo_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = update.message
    if not context.args:
        await msg.reply_text("Usage: /photo @username")
        return
    username = context.args[0].replace("@", "")
    sent = await msg.reply_photo(
        photo="https://files.catbox.moe/k5j9ya.jpg",
        caption="*😉HYE SMLIE PLEASE!! 📷📸!!*",
        parse_mode="Markdown"
    )
    await asyncio.sleep(3)
    try:
        await sent.edit_caption(caption="*😋Wait a Second For Image*", parse_mode="Markdown")
    except:
        pass
    await asyncio.sleep(1)
    try:
        chat_obj = await context.bot.get_chat(f"@{username}")
        photos = await context.bot.get_user_profile_photos(chat_obj.id, limit=1)
        captions = settings.get("photo_captions", [])
        cap_text = random.choice(captions)["text"] if captions else "*😉You Are Looking Cool In Image*"
        if photos and photos.photos:
            await msg.reply_photo(photo=photos.photos[0][-1].file_id, caption=cap_text, parse_mode="Markdown")
        else:
            await msg.reply_text(f"{cap_text}\n@{username}", parse_mode="Markdown")
    except:
        captions = settings.get("photo_captions", [])
        cap_text = random.choice(captions)["text"] if captions else "*😉You Are Looking Cool In Image*"
        await msg.reply_text(f"{cap_text}\n@{username}", parse_mode="Markdown")

async def upcaption_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        return
    if not context.args:
        await update.message.reply_text("Usage: /upcaption <caption text>")
        return
    text = " ".join(context.args)
    settings["caption_counter"] = settings.get("caption_counter", 0) + 1
    cid = settings["caption_counter"]
    settings["photo_captions"].append({"id": cid, "text": text})
    save_data()
    await update.message.reply_text(f"✅ Caption uploaded! ID: `{cid}`", parse_mode="Markdown")

async def caplist_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        return
    captions = settings.get("photo_captions", [])
    if not captions:
        await update.message.reply_text("Koi caption save nahi hai.")
        return
    text = "📝 *Photo Captions:*\n\n"
    for c in captions:
        text += f"🆔 `{c['id']}` → {c['text'][:60]}\n"
    await update.message.reply_text(text, parse_mode="Markdown")

async def dcap_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        return
    if not context.args:
        await update.message.reply_text("Usage: /dcap <id>")
        return
    try:
        member = await chat.get_member(user.id)
        if member.status in ["administrator","creator"] or user.id == ADMIN_ID:
            chat_enabled[chat.id] = False
            await update.message.reply_text("😴 Thodi so leti hoon... /CHATON se jagana!")
    except:
        pass

async def broadcast(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = update.message
    sent = failed = 0
    targets = list(users_started) + list(groups)
    for cid in targets:
        try:
            if msg.reply_to_message:
                await msg.reply_to_message.copy(chat_id=cid)
            elif context.args:
                await context.bot.send_message(cid, " ".join(context.args))
            sent += 1
        except:
            failed += 1
        await asyncio.sleep(0.05)
    await msg.reply_text(f"✅ Broadcast done!\nSent: {sent} | Failed: {failed}")

async def clone_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    if not context.args:
        await update.message.reply_text("Usage: /clone <bot_token>")
        return
    token = context.args[0]
    if token in clones:
        await update.message.reply_text("Yeh bot pehle se clone hai!")
        return
    try:
        clone_app = ApplicationBuilder().token(token).build()
        add_handlers(clone_app)
        asyncio.create_task(clone_app.run_polling(drop_pending_updates=True))
        clones[token] = {"app": clone_app, "owner": user.id}
        await update.message.reply_text(f"✅ Clone ho gaya! Token: `{token[:15]}...`", parse_mode="Markdown")
    except Exception as e:
        await update.message.reply_text(f"❌ Clone failed: {str(e)[:100]}")

async def dclone_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    to_remove = [t for t, d in clones.items() if d["owner"] == user.id]
    for token in to_remove:
        try:
            del clones[token]
        except:
            pass
    await update.message.reply_text(f"✅ {len(to_remove)} clone(s) hata diye!")

async def bbcast(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        await update.message.reply_text("Sirf admin ke liye!")
        return
    msg = update.message
    sent = 0
    for token, data in clones.items():
        app = data["app"]
        for uid in users_started:
            try:
                if msg.reply_to_message:
                    await msg.reply_to_message.copy(chat_id=uid)
                else:
                    await app.bot.send_message(uid, " ".join(context.args) if context.args else "Hello!")
                sent += 1
            except:
                pass
            await asyncio.sleep(0.05)
    await msg.reply_text(f"✅ Admin bcast done via {len(clones)} clones! ~{sent} messages")

async def gfbf_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat = update.effective_chat
    if chat.type not in ["group","supergroup"]:
        await update.message.reply_text("Group mein use karo!")
        return
    if chat.id in gfbf_data and datetime.now() < gfbf_data[chat.id]["expires"]:
        d = gfbf_data[chat.id]
        await update.message.reply_text(f"💑 Aaj ke BF GF:\n🌟 {d['users'][0]} & {d['users'][1]}")
        return
    members = list(recent_group_users.get(chat.id, set()))
    if len(members) < 2:
        await update.message.reply_text("Group mein kam se kam 2 log chahiye!")
        return
    selected = random.sample(members, 2)
    gfbf_data[chat.id] = {"users": selected, "expires": datetime.now() + timedelta(hours=24)}
    await update.message.reply_text(f"🌟 TO DAY BF GF 🎊\n\n💑 {selected[0]} & {selected[1]}\n\nCongratulations! 🎉❤️")

async def cgfbf_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat = update.effective_chat
    user = update.effective_user
    try:
        member = await chat.get_member(user.id)
        if member.status not in ["administrator","creator"] and user.id != ADMIN_ID:
            await update.message.reply_text("Sirf admins!")
            return
    except:
        return
    if not context.args or len(context.args) < 2:
        await update.message.reply_text("Usage: /CGFBF @user1 @user2")
        return
    u1, u2 = context.args[0], context.args[1]
    gfbf_data[chat.id] = {"users": [u1, u2], "expires": datetime.now() + timedelta(hours=24)}
    await update.message.reply_text(f"🌟 CUSTOM BF GF 🎊\n\n💑 {u1} & {u2}\n\nCongratulations! 🎉❤️")

async def bff_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat = update.effective_chat
    if chat.type not in ["group","supergroup"]:
        await update.message.reply_text("Group mein use karo!")
        return
    if chat.id in bff_data and datetime.now() < bff_data[chat.id]["expires"]:
        d = bff_data[chat.id]
        await update.message.reply_text(f"👫 Aaj ke BFF: {d['users'][0]} & {d['users'][1]}! 💙")
        return
    members = list(recent_group_users.get(chat.id, set()))
    if len(members) < 2:
        await update.message.reply_text("Enough data nahi hai!")
        return
    best_pair = tuple(random.sample(members, 2))
    bff_data[chat.id] = {"users": list(best_pair), "expires": datetime.now() + timedelta(hours=24)}
    await update.message.reply_text(f"👫 TODAY'S BEST FRIENDS 💙\n\n🌟 {best_pair[0]} & {best_pair[1]}\n\nIn dono ki dosti sabse gehri hai! 🎊✨")

async def couple_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat = update.effective_chat
    if chat.type not in ["group","supergroup"]:
        await update.message.reply_text("Group mein use karo!")
        return
    members = list(recent_group_users.get(chat.id, set()))
    if len(members) < 2:
        await update.message.reply_text("Kam se kam 2 log chahiye!")
        return
    s = random.sample(members, 2)
    await update.message.reply_text(f"💞 RANDOM COUPLE 💞\n\n❤️ {s[0]} & {s[1]}\n\nKitne cute lagte hain! 😍🎊")

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = update.message
    if not msg:
        return
    chat = update.effective_chat
    user = update.effective_user
    if not user:
        return
    if chat.type in ["group","supergroup"]:
        groups.add(chat.id)
        mention = f"[{user.first_name}](tg://user?id={user.id})"
        recent_group_users[chat.id].add(mention)
        if msg.reply_to_message and msg.reply_to_message.from_user:
            reply_counts[chat.id][user.id][msg.reply_to_message.from_user.id] += 1
    if chat.type == "private":
        users_started.add(user.id)
    if not chat_enabled.get(chat.id, True):
        return
    if msg.text:
        response = await get_ai_response(msg.text, user.first_name or "Tum")
        await msg.reply_text(response)

async def handle_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    if user.id == ADMIN_ID and update.effective_chat.type == "private":
        msg = update.message
        settings["start_photo"] = msg.photo[-1].file_id
        if msg.caption:
            settings["start_caption"] = msg.caption
        save_data()
        await msg.reply_text("✅ Start photo update ho gayi!")
    else:
        if update.effective_chat.type in ["group","supergroup"] and chat_enabled.get(update.effective_chat.id, True):
            response = await get_ai_response("(koi photo bheja)", update.effective_user.first_name or "Tum")
            await update.message.reply_text(response)

async def setcaption(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        return
    if context.args:
        settings["start_caption"] = " ".join(context.args)
        save_data()
        await update.message.reply_text("✅ Caption set!")

async def setbutton(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        return
    if len(context.args) >= 2:
        settings["start_buttons"][context.args[0]] = context.args[1]
        save_data()
        await update.message.reply_text(f"✅ Button set: {context.args[0]} = {context.args[1]}")

def add_handlers(app):
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler(["CHATON","chaton"], chaton))
    app.add_handler(CommandHandler(["CHATOFF","chatoff"], chatoff))
    app.add_handler(CommandHandler(["broadcast","bcast"], broadcast))
    app.add_handler(CommandHandler("clone", clone_cmd))
    app.add_handler(CommandHandler("dclone", dclone_cmd))
    app.add_handler(CommandHandler("bbcast", bbcast))
    app.add_handler(CommandHandler(["GfBF","gfbf","GFBF"], gfbf_cmd))
    app.add_handler(CommandHandler(["CGFBF","cgfbf"], cgfbf_cmd))
    app.add_handler(CommandHandler(["BFF","bff"], bff_cmd))
    app.add_handler(CommandHandler(["COUPLE","couple"], couple_cmd))
    app.add_handler(CommandHandler("setcaption", setcaption))
    app.add_handler(CommandHandler("setbutton", setbutton))
    app.add_handler(MessageHandler(filters.PHOTO, handle_photo))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

if __name__ == "__main__":
    load_data()
    app = ApplicationBuilder().token(BOT_TOKEN).build()
    add_handlers(app)
    print("✅ Sinzhu Bot Starting...")
    app.run_polling(drop_pending_updates=True)
