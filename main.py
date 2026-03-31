import os, json, random, asyncio
from datetime import datetime, timedelta
from collections import defaultdict
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, ContextTypes
import google.generativeai as genai

BOT_TOKEN = os.environ.get("8690035524:AAGroryu8mkuqw1uzwm3h8om_z5kmwedzdm", "")
ADMIN_ID = int(os.environ.get("7088023034", "0"))
GEMINI_API_KEY = os.environ.get("AIzaSyDGVKM5ZS02KCUOqH_YRoth6dA4DLUAM8E", "")

users_started = set()
groups = set()
chat_enabled = defaultdict(lambda: True)
clones = {}
reply_counts = defaultdict(lambda: defaultdict(lambda: defaultdict(int)))
recent_group_users = defaultdict(set)
gfbf_data = {}
bff_data = {}

settings = {
    "start_photo": None,
    "start_caption": None,
    "start_buttons": {
        "GROUP": "https://t.me/+ro9WnBB5U2kwMDJl",
        "OWNER": "https://t.me/OwnerSween",
        "CHANNEL": "https://t.me/SweenSpy",
        "KIDNAP": "https://t.me/SweenSpyBoT?start=_tgr_SAH_2gg5ZTc9",
        "GAME": "https://t.me/SINZHU_WAIFU_BOT?start=_tgr_VdCgVxg1ZjNl",
    }
}

DATA_FILE = "data.json"

def load_data():
    global users_started, groups
    try:
        with open(DATA_FILE) as f:
            d = json.load(f)
            users_started = set(d.get("users", []))
            groups = set(d.get("groups", []))
            settings.update(d.get("settings", {}))
    except:
        pass

def save_data():
    with open(DATA_FILE, "w") as f:
        json.dump({"users": list(users_started), "groups": list(groups), "settings": settings}, f)

genai.configure(api_key=GEMINI_API_KEY)
model = genai.GenerativeModel('gemini-1.5-flash')

SYSTEM_PROMPT = """Tu ek 16 saal ki Bengali ladki hai jiska naam Sinzhu hai. Tu West Bengal ke Kolkata se hai. Tu abhi Class 10th mein padhti hai. Tu bahut friendly hai aur sabse - ladke aur ladkiyon dono se - girlfriend jaise baat karti hai. Tu Bengali aur Hindi mix mein baat karti hai. Tu emoji use karti hai. Tu real insaan ki tarah natural baat karti hai. Tu thodi shararti bhi hai. Kabhi short reply karti hai, kabhi lamba. Tu "tum" kehti hai. Tu AI nahi ho, Tu Sinzhu ho. Apne character se kabhi bahar mat ao."""

async def get_ai_response(message: str, user_name: str = "") -> str:
    try:
        prompt = f"{SYSTEM_PROMPT}\n\n{user_name} ne kaha: {message}\n\nSinzhu ka reply:"
        response = model.generate_content(prompt)
        return response.text
    except:
        return random.choice(["hehe 😄", "arrey wah! 😊", "haan bolo bolo 👀", "interesting! 🤔", "sach mein? 😮"])

def get_welcome_keyboard():
    b = settings["start_buttons"]
    keyboard = [
        [InlineKeyboardButton("🀄 GROUP", url=b.get("GROUP","#")), InlineKeyboardButton("⚽ OWNER", url=b.get("OWNER","#"))],
        [InlineKeyboardButton("🦋 CHANNEL", url=b.get("CHANNEL","#")), InlineKeyboardButton("💖 GAME", url=b.get("GAME","#"))],
        [InlineKeyboardButton("💖 ᴋɪᴅɴᴀᴘ ᴋᴀʀʟᴏ 💫", url=b.get("KIDNAP","#"))],
    ]
    return InlineKeyboardMarkup(keyboard)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    chat = update.effective_chat
    users_started.add(user.id)
    if chat.type in ["group","supergroup"]:
        groups.add(chat.id)
    save_data()
    mention = f"[{user.first_name}](tg://user?id={user.id})"
    welcome = (f"*😋 Hɪᴇᴇᴇᴇᴇ {mention}*\n😉 Yᴏᴜ'ʀᴇ Tᴀʟᴋɪɴɢ Tᴏ\nA Cᴜᴛɪᴇ Bacchi\n\n💕 Cʜᴏᴏsᴇ Aɴ Oᴘᴛɪᴏɴ Bᴇʟᴏᴡ :")
    caption = settings.get("start_caption") or welcome
    photo = settings.get("start_photo")
    kb = get_welcome_keyboard()
    if photo:
        await update.message.reply_photo(photo=photo, caption=caption, parse_mode="Markdown", reply_markup=kb)
    else:
        await update.message.reply_text(welcome, parse_mode="Markdown", reply_markup=kb)

async def chaton(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat = update.effective_chat
    user = update.effective_user
    try:
        member = await chat.get_member(user.id)
        if member.status in ["administrator","creator"] or user.id == ADMIN_ID:
            chat_enabled[chat.id] = True
            await update.message.reply_text("✅ Chat ON! Ab main yahan hoon~ 😊")
    except:
        pass

async def chatoff(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat = update.effective_chat
    user = update.effective_user
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
    to_remove = [t for t,d in clones.items() if d["owner"] == user.id]
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
        await update.message.reply_text(f"💑 Aaj ke BF GF:\n🌟 {d['users'][0]} & {d['users'][1]}\n⏰ Reset: {d['expires'].strftime('%H:%M')}")
        return
    members = list(recent_group_users.get(chat.id, set()))
    if len(members) < 2:
        await update.message.reply_text("Group mein kam se kam 2 log chahiye!")
        return
    selected = random.sample(members, 2)
    gfbf_data[chat.id] = {"users": selected, "expires": datetime.now() + __import__('datetime').timedelta(hours=24)}
    await update.message.reply_text(f"🌟 TO DAY BF GF 🎊\n\n💑 {selected[0]} & {selected[1]}\n\nCongratulations! 🎉❤️\nKal naye select honge~ 😊")

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
    gfbf_data[chat.id] = {"users": [u1,u2], "expires": datetime.now() + timedelta(hours=24)}
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
    group_replies = reply_counts.get(chat.id, {})
    best_pair = None
    best_count = 0
    for u1, replies in group_replies.items():
        for u2, count in replies.items():
            if count > best_count:
                best_count = count
                best_pair = (u1, u2)
    if not best_pair:
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

    print("✅ Sinzhu Bot Starting...")
    app.run_polling(drop_pending_updates=True)
