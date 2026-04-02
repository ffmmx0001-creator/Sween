import os, json, random, asyncio, io, logging
from datetime import datetime, timedelta, date
from collections import defaultdict
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, InputMediaPhoto
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, CallbackQueryHandler, filters, ContextTypes
import google.generativeai as genai

logging.basicConfig(format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO)
logger = logging.getLogger(__name__)

BOT_TOKEN   = os.environ.get("BOT_TOKEN", "")
ADMIN_ID    = int(os.environ.get("ADMIN_ID", "0"))
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "")

users_started = set()
groups        = set()
chat_enabled  = defaultdict(lambda: True)
recent_group_users = defaultdict(set)
gfbf_data = {}
bff_data  = {}
conversation_history = defaultdict(list)
learned_responses    = {}
user_profiles        = {}

cat_users      = {}
uploaded_cats  = {}
shop_cats      = []
cat_counter    = 0
group_message_counter = defaultdict(int)
active_spawns  = {}
coupon_codes   = {}
top_banners    = {"top": None, "topgroups": None}

# ── RARITY ───────────────────────────────────────────────
RARITY_NAMES = {
    1:  "🌟 God Summon",
    2:  "🎀 Only Shop",
    3:  "🔮 Limited",
    4:  "💎 Premium",
    5:  "🎐 Special",
    6:  "💮 Exclusive",
    7:  "🪽 Celestial",
    8:  "🟡 Legendary",
    9:  "🟠 Rare",
    10: "🔵 Medium",
    12: "🟢 Common",
}
RARITY_PRICES = {
    1: 10000, 2: 8000, 3: 6000, 4: 4000,
    5: 3000,  6: 2500, 7: 2000, 8: 1500,
    9: 1000, 10: 500, 12: 200,
}

# ── RANKS ────────────────────────────────────────────────
RANK_TITLES = [
    (0,   "🐾 Kitten Lover"),
    (5,   "🐱 Cat Friend"),
    (10,  "😺 Cat Enthusiast"),
    (20,  "🌸 Fur Baby Parent"),
    (35,  "🐈 Cat Guardian"),
    (50,  "💕 Kitty Caretaker"),
    (75,  "🏡 Cat Shelter"),
    (100, "👑 Cat Royalty"),
    (150, "🌟 Legendary Cat Lord"),
    (200, "🎀 Supreme Pet Lover"),
]

def get_rank_title(total_cats: int) -> str:
    title = RANK_TITLES[0][1]
    for threshold, name in RANK_TITLES:
        if total_cats >= threshold:
            title = name
    return title

# ── SETTINGS ─────────────────────────────────────────────
settings = {
    "photo_list": [], "photo_counter": 0, "start_caption": None,
    "start_buttons": {
        "GROUP":  "https://t.me/+ro9WnBB5U2kwMDJl",
        "OWNER":  "https://t.me/OwnerSween",
        "CHANNEL":"https://t.me/SweenSpy",
        "KIDNAP": "https://t.me/SweenSpyBoT?start=start",
        "GAME":   "https://t.me/SINZHU_WAIFU_BOT?start=start",
    },
    "custom_replies": {}, "voice_messages": {}, "voice_counter": 0,
    "status_caption": "🗿Total Users : {users}\n🌐 Total Groups : {groups}",
    "photo_captions": [], "caption_counter": 0,
    "ai_learning": True, "learning_data": {},
}

DATA_FILE     = "data.json"
MAX_HISTORY   = 20
MAX_LEARN_PER_KEY = 15
SPAWN_INTERVAL = 15

# ══════════════════════════════════════════════════════════
#                   DATA LOAD / SAVE
# ══════════════════════════════════════════════════════════

def load_data():
    global users_started, groups, learned_responses, user_profiles
    global cat_users, uploaded_cats, shop_cats, cat_counter, coupon_codes
    try:
        with open(DATA_FILE) as f:
            d = json.load(f)
        users_started = set(d.get("users", []))
        groups        = set(d.get("groups", []))
        learned_responses = d.get("learned_responses", {})
        user_profiles     = d.get("user_profiles", {})
        cat_users     = {int(k): v for k, v in d.get("cat_users", {}).items()}
        uploaded_cats = {int(k): v for k, v in d.get("uploaded_cats", {}).items()}
        shop_cats     = d.get("shop_cats", [])
        cat_counter   = d.get("cat_counter", 0)
        coupon_codes  = d.get("coupon_codes", {})
        for k, v in d.get("settings", {}).items():
            settings[k] = v
        for key in ["voice_messages","custom_replies","learning_data"]:
            if key not in settings: settings[key] = {}
        for key in ["photo_list","photo_captions"]:
            if key not in settings: settings[key] = []
        for key in ["voice_counter","photo_counter","caption_counter"]:
            if key not in settings: settings[key] = 0
        if "ai_learning"    not in settings: settings["ai_learning"] = True
        if "status_caption" not in settings:
            settings["status_caption"] = "🗿Total Users : {users}\n🌐 Total Groups : {groups}"
        # restore banners
        top_banners["top"]       = settings.get("topbanner_top")
        top_banners["topgroups"] = settings.get("topbanner_topgroups")
    except Exception as e:
        logger.warning(f"Load error: {e}")

def save_data():
    try:
        with open(DATA_FILE, "w") as f:
            json.dump({
                "users": list(users_started), "groups": list(groups),
                "settings": settings,
                "learned_responses": learned_responses,
                "user_profiles": user_profiles,
                "cat_users":     {str(k): v for k, v in cat_users.items()},
                "uploaded_cats": {str(k): v for k, v in uploaded_cats.items()},
                "shop_cats": shop_cats, "cat_counter": cat_counter,
                "coupon_codes": coupon_codes,
            }, f, ensure_ascii=False, indent=2)
    except Exception as e:
        logger.error(f"Save error: {e}")

def get_or_create_user(user_id: int, first_name: str = "User"):
    if user_id not in cat_users:
        cat_users[user_id] = {
            "name": first_name, "family_name": None, "family_name_set": False,
            "coins": 0, "cats": [], "inventory": {"milk": 0, "food": 0},
            "daily_last": None, "weekly_last": None,
            "hclaim_last": None, "milk_last": {},
        }
    if "inventory" not in cat_users[user_id]:
        cat_users[user_id]["inventory"] = {"milk": 0, "food": 0}
    return cat_users[user_id]

def today_str(): return date.today().isoformat()
def week_str():  return f"{date.today().isocalendar()[0]}-W{date.today().isocalendar()[1]}"

# ══════════════════════════════════════════════════════════
#                       AI SYSTEM
# ══════════════════════════════════════════════════════════

genai.configure(api_key=GEMINI_API_KEY)
ai_model = genai.GenerativeModel("gemini-1.5-flash")

SYSTEM_PROMPT = (
    "Tu ek 16 saal ki Bengali ladki hai jiska naam Sinzhu hai. Tu Kolkata se hai, Class 10th mein padhti hai. "
    "Tu Hinglish mein chhoti, natural aur expressive replies deti hai. Kabhi kabhi Bengali words bhi use karti hai. "
    "Tu emojis use karti hai lekin zyada nahi. Tu ek real ladki jaisi baat karti hai, AI nahi. "
    "Girlfriend style mein warm aur caring replies deti hai. Agar koi rude ho toh thoda attitude dikhati hai. "
    "Tu logon ki baaton se seekhti hai. Apni real identity kabhi reveal mat karna."
)

def learn_from_conversation(user_id, user_msg, bot_reply):
    if not settings.get("ai_learning", True): return
    uid = str(user_id)
    if uid not in user_profiles: user_profiles[uid] = {"messages": 0}
    user_profiles[uid]["messages"] = user_profiles[uid].get("messages", 0) + 1
    for word in user_msg.lower().split():
        if len(word) > 3 and word.isalpha():
            if word not in learned_responses: learned_responses[word] = []
            if bot_reply not in learned_responses[word]:
                learned_responses[word].append(bot_reply)
                if len(learned_responses[word]) > MAX_LEARN_PER_KEY:
                    learned_responses[word].pop(0)
    if sum(p.get("messages",0) for p in user_profiles.values()) % 10 == 0:
        save_data()

def get_user_context(user_id):
    msgs = user_profiles.get(str(user_id), {}).get("messages", 0)
    if msgs > 100: return "Yeh mera purana dost hai, zyada comfortable ho ke baat kar."
    if msgs > 20:  return "Yeh user mujhse pehle bhi baat kar chuka hai."
    return "Yeh user new hai, friendly reh."

async def get_ai_response(message, display_name, user_id):
    try:
        history = conversation_history[user_id]
        prompt  = (f"{SYSTEM_PROMPT}\n\nContext: {get_user_context(user_id)}\n\n"
                   f"{display_name} ne kaha: {message}\n\nSinzhu ka reply (short, 1-2 lines max):")
        chat    = ai_model.start_chat(history=list(history[-MAX_HISTORY:]))
        reply   = chat.send_message(prompt).text.strip()
        history.append({"role": "user",  "parts": [f"{display_name}: {message}"]})
        history.append({"role": "model", "parts": [reply]})
        if len(history) > MAX_HISTORY * 2:
            conversation_history[user_id] = history[-MAX_HISTORY * 2:]
        learn_from_conversation(user_id, message, reply)
        uid = str(user_id)
        if uid not in user_profiles: user_profiles[uid] = {"messages": 0}
        user_profiles[uid]["messages"] = user_profiles[uid].get("messages", 0) + 1
        return reply
    except Exception as e:
        logger.error(f"AI error: {e}")
        return random.choice(["hehe 😄","arrey wah! 😊","haan bolo 👀","sach mein? 😮","lol 😂"])

def get_display_name(user): return user.first_name or "Tum"

def get_custom_reply(text):
    tl = text.lower().strip()
    for kw, rep in settings["custom_replies"].items():
        if kw.lower() in tl: return rep
    return None

def get_voice_for_text(text):
    tl = text.lower()
    matches = [v["file_id"] for v in settings["voice_messages"].values()
               if v.get("keyword","").lower() in tl]
    return random.choice(matches) if matches else None

def get_welcome_keyboard():
    b = settings["start_buttons"]
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🀄 GROUP",   url=b.get("GROUP","#")),
         InlineKeyboardButton("⚽ OWNER",   url=b.get("OWNER","#"))],
        [InlineKeyboardButton("🦋 CHANNEL", url=b.get("CHANNEL","#")),
         InlineKeyboardButton("💖 GAME",    url=b.get("GAME","#"))],
        [InlineKeyboardButton("💖 ᴋɪᴅɴᴀᴘ ᴋᴀʀʟᴏ 💫", url=b.get("KIDNAP","#"))],
    ])

async def is_admin_or_owner(update):
    user = update.effective_user
    if user.id == ADMIN_ID: return True
    try:
        m = await update.effective_chat.get_member(user.id)
        return m.status in ["administrator","creator"]
    except: return False

# ══════════════════════════════════════════════════════════
#                   CAT FAMILY SYSTEM
# ══════════════════════════════════════════════════════════

def build_family_keyboard(target_uid, cats, page):
    per_page  = 6
    total     = max(1, (len(cats) + per_page - 1) // per_page)
    page      = max(0, min(page, total - 1))
    page_cats = cats[page*per_page:(page+1)*per_page]
    buttons, row = [], []
    for cat in page_cats:
        r    = cat.get("rarity", 12)
        name = cat.get("name", f"Cat#{cat['id']}")
        row.append(InlineKeyboardButton(
            f"{'⭐'*min(r,5)} {name}",
            callback_data=f"catview_{target_uid}_{cat['id']}_{page}"
        ))
        if len(row) == 2: buttons.append(row); row = []
    if row: buttons.append(row)
    nav = []
    if page > 0:       nav.append(InlineKeyboardButton("◀️", callback_data=f"family_{target_uid}_{page-1}"))
    nav.append(InlineKeyboardButton(f"📄 {page+1}/{total}", callback_data="noop"))
    if page < total-1: nav.append(InlineKeyboardButton("▶️", callback_data=f"family_{target_uid}_{page+1}"))
    if nav: buttons.append(nav)
    buttons.append([InlineKeyboardButton("❌ Close", callback_data=f"closefam_{target_uid}")])
    return InlineKeyboardMarkup(buttons)

async def profile_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    data = get_or_create_user(user.id, user.first_name)
    mention     = f"[{user.first_name}](tg://user?id={user.id})"
    family_name = data.get("family_name") or "No Family Set"
    cats        = data.get("cats", [])
    all_sorted  = sorted(cat_users.items(), key=lambda x: len(x[1].get("cats",[])), reverse=True)
    rank        = next((i+1 for i,(uid,_) in enumerate(all_sorted) if uid==user.id), len(all_sorted))
    rank_title  = get_rank_title(len(cats))
    inv         = data.get("inventory", {})
    text = (
        f"*[Cat Family]*\n\n"
        f"❇️ Owner: {mention}\n"
        f"🏠 Family: *{family_name}*\n"
        f"🌟 Rank: *#{rank}* — {rank_title}\n"
        f"😸 Total Cats: *{len(cats)}*\n"
        f"💰 Coins: *{data.get('coins',0)}*\n"
        f"🍼 Milk: *{inv.get('milk',0)}*  🥫 Food: *{inv.get('food',0)}*"
    )
    kb = InlineKeyboardMarkup([[InlineKeyboardButton("👀 See Family", callback_data=f"family_{user.id}_0")]])
    await update.message.reply_text(text, parse_mode="Markdown", reply_markup=kb)

async def family_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query; await query.answer()
    parts      = query.data.split("_")
    target_uid = int(parts[1])
    page       = int(parts[2]) if len(parts) > 2 else 0
    data       = cat_users.get(target_uid)
    if not data: await query.answer("User data nahi mila.", show_alert=True); return
    cats = data.get("cats", [])
    if not cats:
        await query.edit_message_reply_markup(reply_markup=InlineKeyboardMarkup([[
            InlineKeyboardButton("😿 Koi cat nahi abhi", callback_data="noop")
        ]])); return
    await query.edit_message_reply_markup(reply_markup=build_family_keyboard(target_uid, cats, page))

async def catview_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query; await query.answer()
    parts      = query.data.split("_")
    target_uid = int(parts[1]); cat_id = int(parts[2])
    back_page  = int(parts[3]) if len(parts) > 3 else 0
    data       = cat_users.get(target_uid)
    if not data: await query.answer("User data nahi mila.", show_alert=True); return
    cat = next((c for c in data.get("cats",[]) if c["id"]==cat_id), None)
    if not cat: await query.answer("Cat nahi mili.", show_alert=True); return
    rarity = cat.get("rarity", 12)
    caption = (
        f"🐱 *{cat.get('name',f'Cat#{cat_id}')}*\n\n"
        f"✨ Rarity: {'⭐'*min(rarity,5)} {RARITY_NAMES.get(rarity,'?')}\n"
        f"🍼 Milk Given: *{cat.get('milk',0)}* times\n"
        f"🆔 Cat ID: *#{cat_id}*"
    )
    kb = InlineKeyboardMarkup([[
        InlineKeyboardButton("🔙 Gallery Wapas", callback_data=f"family_{target_uid}_{back_page}")
    ]])
    try:
        await context.bot.send_photo(
            chat_id=query.message.chat_id, photo=cat["file_id"],
            caption=caption, parse_mode="Markdown", reply_markup=kb
        )
    except Exception as e:
        logger.warning(f"Catview: {e}")
        await query.answer("Photo load nahi hui.", show_alert=True)

async def closefam_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query; await query.answer()
    parts      = query.data.split("_")
    target_uid = int(parts[1])
    data       = cat_users.get(target_uid)
    cats       = data.get("cats",[]) if data else []
    fname      = data.get("name","User") if data else "User"
    fam        = (data.get("family_name") or "No Family") if data else "No Family"
    all_sorted = sorted(cat_users.items(), key=lambda x: len(x[1].get("cats",[])), reverse=True)
    rank       = next((i+1 for i,(uid,_) in enumerate(all_sorted) if uid==target_uid), "?")
    text = (
        f"*[Cat Family]*\n\n"
        f"❇️ Owner: [{fname}](tg://user?id={target_uid})\n"
        f"🏠 Family: *{fam}*\n"
        f"🌟 Rank: *#{rank}* — {get_rank_title(len(cats))}\n"
        f"😸 Total Cats: *{len(cats)}*"
    )
    kb = InlineKeyboardMarkup([[InlineKeyboardButton("👀 See Family", callback_data=f"family_{target_uid}_0")]])
    try: await query.edit_message_text(text, parse_mode="Markdown", reply_markup=kb)
    except: await query.edit_message_reply_markup(reply_markup=kb)

async def setfamily_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    data = get_or_create_user(user.id, user.first_name)
    if not context.args:
        await update.message.reply_text("Usage: /setfamily <Family Name>\nPehli baar free, baad mein 500 coins."); return
    new_name = " ".join(context.args)
    if data.get("family_name_set", False):
        if data.get("coins",0) < 500:
            await update.message.reply_text(f"❌ 500 coins chahiye! Tumhare paas: {data['coins']}"); return
        data["coins"] -= 500
        save_data()
        data["family_name"] = new_name
        await update.message.reply_text(f"✅ Family naam: *{new_name}*\n💰 500 coins kat gaye.", parse_mode="Markdown")
    else:
        data["family_name"]     = new_name
        data["family_name_set"] = True
        save_data()
        await update.message.reply_text(f"✅ Family naam: *{new_name}* (Free!) 🎉", parse_mode="Markdown")

async def setcatname_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    data = get_or_create_user(user.id, user.first_name)
    if len(context.args) < 2:
        await update.message.reply_text("Usage: /setcatname <cat_id> <naam>"); return
    try: cat_id = int(context.args[0])
    except: await update.message.reply_text("❌ Cat ID number hona chahiye."); return
    cat = next((c for c in data.get("cats",[]) if c["id"]==cat_id), None)
    if not cat: await update.message.reply_text(f"❌ Cat #{cat_id} tumhare paas nahi."); return
    cat["name"] = " ".join(context.args[1:])
    save_data()
    await update.message.reply_text(f"✅ Cat #{cat_id} ka naam *{cat['name']}* rakh diya! 🐱", parse_mode="Markdown")

async def milk_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    data = get_or_create_user(user.id, user.first_name)
    cats = data.get("cats", [])
    if not cats: await update.message.reply_text("❌ Pehle koi billi adopt karo! /hclaim se free billi lo."); return
    if context.args:
        try:
            cid = int(context.args[0])
            cat = next((c for c in cats if c["id"]==cid), None)
            if not cat: await update.message.reply_text(f"❌ Cat #{cid} tumhare paas nahi."); return
        except: cat = cats[0]
    else: cat = cats[0]
    milk_log   = data.get("milk_last", {})
    cid_str    = str(cat["id"])
    if milk_log.get(cid_str) == today_str():
        await update.message.reply_text(f"🍼 {cat.get('name','Billi')} ko aaj milk pila diya! Kal phir. 😸"); return
    cat["milk"]        = cat.get("milk",0) + 1
    milk_log[cid_str]  = today_str()
    data["milk_last"]  = milk_log
    save_data()
    await update.message.reply_text(
        f"🍼 *{cat.get('name','Billi')}* ko milk pila diya! 😻\nTotal: *{cat['milk']}* times 🐾",
        parse_mode="Markdown"
    )

# ── SHOP ─────────────────────────────────────────────────
async def show_shop_page(target, data, page, user_id):
    if not shop_cats:
        text = (f"🛒 *Cat Store*\n\n💰 Coins: *{data.get('coins',0)}*\n\n"
                f"🍼 Milk — 50 coins\n🥫 Cat Food — 100 coins\n\n_Koi cat shop mein nahi._")
        kb = InlineKeyboardMarkup([[
            InlineKeyboardButton("🍼 Milk (50c)",  callback_data="buyitem_milk_50"),
            InlineKeyboardButton("🥫 Food (100c)", callback_data="buyitem_food_100"),
        ]])
        if hasattr(target, "reply_text"):
            await target.reply_text(text, parse_mode="Markdown", reply_markup=kb)
        else:
            try: await target.edit_message_text(text, parse_mode="Markdown", reply_markup=kb)
            except: pass
        return
    page    = max(0, min(page, len(shop_cats)-1))
    cat_id  = shop_cats[page]
    cdata   = uploaded_cats.get(cat_id)
    if not cdata: return
    rarity  = cdata.get("rarity", 12)
    price   = RARITY_PRICES.get(rarity, 200)
    caption = (
        f"🛒 *Cat Store* [{page+1}/{len(shop_cats)}]\n\n"
        f"🐱 Cat ID: *#{cat_id}*\n"
        f"✨ Rarity: *{RARITY_NAMES.get(rarity,'?')}*\n"
        f"💰 Price: *{price} coins*\n\n"
        f"👛 Tumhare Coins: *{data.get('coins',0)}*"
    )
    nav = []
    if page > 0:                nav.append(InlineKeyboardButton("◀️", callback_data=f"shopnav_{user_id}_{page-1}"))
    nav.append(InlineKeyboardButton(f"🐱 {page+1}/{len(shop_cats)}", callback_data="noop"))
    if page < len(shop_cats)-1: nav.append(InlineKeyboardButton("▶️", callback_data=f"shopnav_{user_id}_{page+1}"))
    kb = InlineKeyboardMarkup([
        nav,
        [InlineKeyboardButton(f"🛍️ Buy ({price}c)", callback_data=f"buycat_{cat_id}_{price}")],
        [InlineKeyboardButton("🍼 Milk (50c)",  callback_data="buyitem_milk_50"),
         InlineKeyboardButton("🥫 Food (100c)", callback_data="buyitem_food_100")],
    ])
    if hasattr(target, "reply_photo"):
        await target.reply_photo(photo=cdata["file_id"], caption=caption, parse_mode="Markdown", reply_markup=kb)
    else:
        try:
            await target.edit_media(
                media=InputMediaPhoto(media=cdata["file_id"], caption=caption, parse_mode="Markdown"),
                reply_markup=kb
            )
        except Exception as e: logger.warning(f"Shop edit: {e}")

async def store_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    data = get_or_create_user(user.id, user.first_name)
    await show_shop_page(update.message, data, 0, user.id)

async def store_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query; await query.answer()
    user  = query.from_user
    data  = get_or_create_user(user.id, user.first_name)
    d     = query.data
    if d.startswith("shopnav_"):
        page = int(d.split("_")[2])
        await show_shop_page(query.message, data, page, user.id)
    elif d.startswith("buycat_"):
        parts  = d.split("_"); cat_id = int(parts[1]); price = int(parts[2])
        if data.get("coins",0) < price:
            await query.answer(f"❌ {price} coins chahiye, tumhare paas {data['coins']}.", show_alert=True); return
        cdata = uploaded_cats.get(cat_id)
        if cat_id not in shop_cats or not cdata:
            await query.answer("❌ Cat available nahi.", show_alert=True); return
        data["coins"] -= price
        data["cats"].append({"id":cat_id,"file_id":cdata["file_id"],"rarity":cdata["rarity"],"name":f"Cat#{cat_id}","milk":0})
        shop_cats.remove(cat_id); save_data()
        await query.answer(f"✅ Cat #{cat_id} khareed li! -{price} coins 🎉", show_alert=True)
    elif d.startswith("buyitem_"):
        parts = d.split("_"); item = parts[1]; price = int(parts[2])
        if data.get("coins",0) < price:
            await query.answer(f"❌ {price} coins chahiye!", show_alert=True); return
        data["coins"] -= price
        inv = data.get("inventory", {"milk":0,"food":0})
        key = "milk" if item=="milk" else "food"
        inv[key] = inv.get(key,0) + 1
        data["inventory"] = inv; save_data()
        await query.answer(f"✅ {'Milk 🍼' if item=='milk' else 'Cat Food 🥫'} khareed li! -{price} coins", show_alert=True)

async def sell_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    data = get_or_create_user(user.id, user.first_name)
    if not context.args: await update.message.reply_text("Usage: /sell <cat_id>"); return
    try: cat_id = int(context.args[0])
    except: await update.message.reply_text("❌ Cat ID number dena hoga."); return
    cat = next((c for c in data.get("cats",[]) if c["id"]==cat_id), None)
    if not cat: await update.message.reply_text(f"❌ Cat #{cat_id} tumhare paas nahi."); return
    sell_price    = int(RARITY_PRICES.get(cat.get("rarity",12),200)*0.4)
    data["cats"]  = [c for c in data["cats"] if c["id"]!=cat_id]
    data["coins"] = data.get("coins",0) + sell_price
    save_data()
    await update.message.reply_text(
        f"💰 *{cat.get('name','Cat')}* bech di!\nMile: *{sell_price} coins* 🪙", parse_mode="Markdown"
    )

async def gift_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    data = get_or_create_user(user.id, user.first_name)
    msg  = update.message
    if not msg.reply_to_message:
        await msg.reply_text("Kisi ke message ki reply mein `/gift <cat_id>` likho.", parse_mode="Markdown"); return
    if not context.args:
        await msg.reply_text("Usage: `/gift <cat_id>`", parse_mode="Markdown"); return
    try: cat_id = int(context.args[0])
    except: await msg.reply_text("❌ Cat ID number."); return
    recip = msg.reply_to_message.from_user
    if recip.id == user.id: await msg.reply_text("❌ Apne aap ko nahi!"); return
    if recip.is_bot:         await msg.reply_text("❌ Bot ko nahi!"); return
    cat = next((c for c in data.get("cats",[]) if c["id"]==cat_id), None)
    if not cat: await msg.reply_text(f"❌ Cat #{cat_id} tumhare paas nahi."); return
    rdata        = get_or_create_user(recip.id, recip.first_name)
    data["cats"] = [c for c in data["cats"] if c["id"]!=cat_id]
    rdata["cats"].append(cat); save_data()
    s = f"[{user.first_name}](tg://user?id={user.id})"
    r = f"[{recip.first_name}](tg://user?id={recip.id})"
    await msg.reply_text(f"🎁 *{s}* ne *{r}* ko *{cat.get('name','Cat')}* gift ki! 💖", parse_mode="Markdown")

async def daily_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    data = get_or_create_user(user.id, user.first_name)
    if data.get("daily_last") == today_str():
        await update.message.reply_text("❌ Aaj ka daily le chuke ho! Kal wapas aao. 🌙"); return
    reward             = random.randint(100, 200)
    data["coins"]      = data.get("coins",0) + reward
    data["daily_last"] = today_str()
    save_data()
    await update.message.reply_text(
        f"🎉 *Daily Reward!*\n\n💰 +{reward} coins!\n💳 Total: {data['coins']}", parse_mode="Markdown"
    )

async def weekly_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    data = get_or_create_user(user.id, user.first_name)
    if data.get("weekly_last") == week_str():
        await update.message.reply_text("❌ Is hafte ka weekly le chuke ho! Agli hafte aao. 🗓️"); return
    reward              = random.randint(500, 1000)
    data["coins"]       = data.get("coins",0) + reward
    data["weekly_last"] = week_str()
    save_data()
    await update.message.reply_text(
        f"🎊 *Weekly Reward!*\n\n💰 +{reward} coins!\n💳 Total: {data['coins']}", parse_mode="Markdown"
    )

async def coupon_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    data = get_or_create_user(user.id, user.first_name)
    if not context.args: await update.message.reply_text("Usage: /coupon <code>"); return
    code   = context.args[0].upper()
    coupon = coupon_codes.get(code)
    if not coupon: await update.message.reply_text("❌ Invalid coupon code."); return
    used_by = coupon.get("used_by", [])
    if user.id in used_by: await update.message.reply_text("❌ Pehle use kar chuke ho!"); return
    uses = coupon.get("uses_left")
    if uses is not None and uses <= 0: await update.message.reply_text("❌ Coupon expire ho gaya."); return
    coins          = coupon.get("coins", 0)
    data["coins"]  = data.get("coins",0) + coins
    used_by.append(user.id); coupon["used_by"] = used_by
    if uses is not None: coupon["uses_left"] = uses - 1
    save_data()
    await update.message.reply_text(
        f"✅ Coupon *{code}* redeem!\n💰 +{coins} coins!\n💳 Total: {data['coins']}", parse_mode="Markdown"
    )

async def hclaim_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    data = get_or_create_user(user.id, user.first_name)
    if data.get("hclaim_last") == today_str():
        await update.message.reply_text("❌ Aaj ka free claim le chuke ho! Kal aana. 🌙"); return
    if not uploaded_cats:
        await update.message.reply_text("❌ Abhi koi cat available nahi."); return
    owned  = {c["id"] for c in data.get("cats",[])}
    pool   = [cid for cid in uploaded_cats if cid not in owned] or list(uploaded_cats.keys())
    cat_id = random.choice(pool)
    cdata  = uploaded_cats[cat_id]
    rarity = cdata.get("rarity", 12)
    b_coins = random.randint(50, 150)
    b_milk  = random.randint(1, 3)
    b_food  = random.randint(1, 2)
    data["cats"].append({"id":cat_id,"file_id":cdata["file_id"],"rarity":rarity,"name":f"Cat#{cat_id}","milk":0})
    data["hclaim_last"] = today_str()
    data["coins"]       = data.get("coins",0) + b_coins
    inv = data.get("inventory", {"milk":0,"food":0})
    inv["milk"] = inv.get("milk",0) + b_milk
    inv["food"] = inv.get("food",0) + b_food
    data["inventory"] = inv
    save_data()
    mention = f"[{user.first_name}](tg://user?id={user.id})"
    caption = (
        f"🎁 *Daily Claim!*\n\n"
        f"😸 {mention} ko mila:\n\n"
        f"🐱 Cat #{cat_id} — {RARITY_NAMES.get(rarity,'?')}\n"
        f"💰 +{b_coins} Coins\n"
        f"🍼 +{b_milk} Milk\n"
        f"🥫 +{b_food} Cat Food\n\n"
        f"_/setcatname {cat_id} <naam> se naam rakho!_"
    )
    try:
        await update.message.reply_photo(photo=cdata["file_id"], caption=caption, parse_mode="Markdown")
    except:
        await update.message.reply_text(caption, parse_mode="Markdown")

# ── SPAWN ─────────────────────────────────────────────────
async def spawn_cat(chat_id, context):
    if not uploaded_cats: return
    cat_id = random.choice(list(uploaded_cats.keys()))
    cdata  = uploaded_cats[cat_id]
    rarity = cdata.get("rarity",12)
    caption = (
        f"🐈‍⬛🐾 *ADOPT ME!*\n\n"
        f"A *{RARITY_NAMES.get(rarity,'?')}* cat appeared!\n\n"
        f"Type `/adop` to claim cat 💖"
    )
    kb = InlineKeyboardMarkup([[InlineKeyboardButton("🐈‍⬛🐾 ADOPT ME", callback_data=f"adopt_{cat_id}")]])
    try:
        sent = await context.bot.send_photo(
            chat_id=chat_id, photo=cdata["file_id"],
            caption=caption, parse_mode="Markdown", reply_markup=kb
        )
        active_spawns[chat_id] = {"cat_id":cat_id,"file_id":cdata["file_id"],"rarity":rarity,"message_id":sent.message_id}
    except Exception as e: logger.warning(f"Spawn: {e}")

async def adop_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat = update.effective_chat; user = update.effective_user
    if chat.type not in ["group","supergroup"]:
        await update.message.reply_text("❌ Sirf groups mein!"); return
    if chat.id not in active_spawns:
        await update.message.reply_text("❌ Abhi koi cat spawn nahi hui!"); return
    spawn = active_spawns.pop(chat.id)
    data  = get_or_create_user(user.id, user.first_name)
    data["cats"].append({"id":spawn["cat_id"],"file_id":spawn["file_id"],"rarity":spawn["rarity"],"name":f"Cat#{spawn['cat_id']}","milk":0})
    save_data()
    try: await context.bot.edit_message_reply_markup(chat_id=chat.id, message_id=spawn["message_id"], reply_markup=None)
    except: pass
    mention = f"[{user.first_name}](tg://user?id={user.id})"
    await update.message.reply_text(
        f"🎉 {mention} ne *Cat #{spawn['cat_id']}* adopt kar li! 💖\n"
        f"✨ {RARITY_NAMES.get(spawn['rarity'],'?')}\n"
        f"_/setcatname {spawn['cat_id']} <naam>_",
        parse_mode="Markdown"
    )

async def adopt_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query; await query.answer()
    chat  = query.message.chat;   user = query.from_user
    if chat.id not in active_spawns:
        await query.answer("❌ Pehle hi adopt ho chuki!", show_alert=True); return
    spawn = active_spawns.pop(chat.id)
    data  = get_or_create_user(user.id, user.first_name)
    data["cats"].append({"id":spawn["cat_id"],"file_id":spawn["file_id"],"rarity":spawn["rarity"],"name":f"Cat#{spawn['cat_id']}","milk":0})
    save_data()
    mention = f"[{user.first_name}](tg://user?id={user.id})"
    try:
        await query.edit_message_caption(
            caption=f"✅ *{mention}* ne adopt kar li!\n✨ {RARITY_NAMES.get(spawn['rarity'],'?')} Cat #{spawn['cat_id']}",
            parse_mode="Markdown", reply_markup=None
        )
    except: pass
    await context.bot.send_message(
        chat_id=chat.id,
        text=f"🎉 {mention} ne *Cat #{spawn['cat_id']}* adopt kar li! 💖\n_/setcatname {spawn['cat_id']} <naam>_",
        parse_mode="Markdown"
    )

# ── LEADERBOARD ──────────────────────────────────────────
async def top_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not cat_users:
        await update.message.reply_text("❌ Abhi koi player nahi hai!"); return
    top_10 = sorted(cat_users.items(), key=lambda x: len(x[1].get("cats",[])), reverse=True)[:10]
    medals = ["🥇","🥈","🥉","4️⃣","5️⃣","6️⃣","7️⃣","8️⃣","9️⃣","🔟"]
    text   = "🏆 *TOP CAT LOVERS* 🐱\n\n"
    for i,(uid,data) in enumerate(top_10):
        name  = data.get("name","User")
        cats  = len(data.get("cats",[]))
        coins = data.get("coins",0)
        text += f"{medals[i]} [{name}](tg://user?id={uid})\n"
        text += f"   😸 {cats} cats | 💰 {coins} coins\n"
        text += f"   {get_rank_title(cats)}\n\n"
    if top_banners.get("top"):
        try:
            await update.message.reply_photo(photo=top_banners["top"], caption=text, parse_mode="Markdown"); return
        except Exception as e: logger.warning(f"Top banner: {e}")
    await update.message.reply_text(text, parse_mode="Markdown")

async def topgroups_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not cat_users:
        await update.message.reply_text("❌ Abhi koi data nahi!"); return
    group_totals = {}
    for gid, members_set in recent_group_users.items():
        total_cats = total_users = 0
        for uid, udata in cat_users.items():
            mention = f"[{udata.get('name','User')}](tg://user?id={uid})"
            if mention in members_set:
                total_cats  += len(udata.get("cats",[]))
                total_users += 1
        if total_cats > 0:
            group_totals[gid] = {"cats":total_cats,"users":total_users}
    if not group_totals:
        await update.message.reply_text("❌ Abhi koi group data nahi! Groups mein khelna shuru karo."); return
    sorted_groups = sorted(group_totals.items(), key=lambda x: x[1]["cats"], reverse=True)[:10]
    medals = ["🥇","🥈","🥉","4️⃣","5️⃣","6️⃣","7️⃣","8️⃣","9️⃣","🔟"]
    text   = "🏆 *TOP CAT LOVER GROUPS* 🐈‍⬛\n\n"
    for i,(gid,stats) in enumerate(sorted_groups):
        try:
            chat_obj = await context.bot.get_chat(gid)
            gname    = chat_obj.title or f"Group {gid}"
        except: gname = f"Group #{i+1}"
        text += f"{medals[i]} *{gname}*\n"
        text += f"   😸 {stats['cats']} cats | 👥 {stats['users']} players\n\n"
    if top_banners.get("topgroups"):
        try:
            await update.message.reply_photo(photo=top_banners["topgroups"], caption=text, parse_mode="Markdown"); return
        except Exception as e: logger.warning(f"Topgroups banner: {e}")
    await update.message.reply_text(text, parse_mode="Markdown")

async def settopbanner_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID: return
    msg   = update.message
    reply = msg.reply_to_message
    if not context.args:
        await msg.reply_text(
            "Usage: Photo ki reply mein likho:\n"
            "`/settopbanner top` — /top ka banner\n"
            "`/settopbanner topgroups` — /topgroups ka banner",
            parse_mode="Markdown"
        ); return
    which = context.args[0].lower()
    if which not in ("top","topgroups"):
        await msg.reply_text("❌ `top` ya `topgroups` likho.", parse_mode="Markdown"); return
    if not reply or not reply.photo:
        await msg.reply_text("❌ Kisi photo ki reply mein yeh command likho!"); return
    file_id = reply.photo[-1].file_id
    top_banners[which]             = file_id
    settings[f"topbanner_{which}"] = file_id
    save_data()
    await msg.reply_text(f"✅ `/{'top' if which=='top' else 'topgroups'}` ka banner set!", parse_mode="Markdown")

# ── ADMIN CAT COMMANDS ────────────────────────────────────
async def upload_cat_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID: return
    global cat_counter
    msg   = update.message; reply = msg.reply_to_message
    valid = ", ".join(str(k) for k in sorted(RARITY_NAMES))
    if not reply or not reply.photo:
        await msg.reply_text(f"❌ Cat photo ki reply mein `/upload <rarity>` likho!\nValid: {valid}", parse_mode="Markdown"); return
    if not context.args:
        await msg.reply_text("❌ Rarity do: `/upload 8`", parse_mode="Markdown"); return
    try:
        r = int(context.args[0])
        if r not in RARITY_NAMES: raise ValueError
    except:
        await msg.reply_text(f"❌ Valid rarity: {valid}"); return
    cat_counter += 1
    uploaded_cats[cat_counter] = {"file_id": reply.photo[-1].file_id, "rarity": r}
    save_data()
    await msg.reply_text(
        f"✅ Cat uploaded!\n🆔 ID: `{cat_counter}` | {RARITY_NAMES[r]}\n📸 Total: {len(uploaded_cats)}",
        parse_mode="Markdown"
    )

async def addshop_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID: return
    if not context.args: await update.message.reply_text("Usage: /addshop <cat_id>"); return
    try: cid = int(context.args[0])
    except: await update.message.reply_text("❌ Number."); return
    if cid not in uploaded_cats: await update.message.reply_text(f"❌ Cat #{cid} uploaded nahi."); return
    if cid in shop_cats:         await update.message.reply_text(f"❌ Cat #{cid} pehle se shop mein."); return
    shop_cats.append(cid); save_data()
    await update.message.reply_text(f"✅ Cat #{cid} shop mein! 🛒 Total: {len(shop_cats)}")

async def rshop_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID: return
    if not context.args: await update.message.reply_text("Usage: /rshop <cat_id>"); return
    try: cid = int(context.args[0])
    except: await update.message.reply_text("❌ Number."); return
    if cid in shop_cats: shop_cats.remove(cid); save_data(); await update.message.reply_text(f"✅ Cat #{cid} shop se hata!")
    else: await update.message.reply_text(f"❌ Cat #{cid} shop mein nahi.")

async def decat_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID: return
    if not context.args: await update.message.reply_text("Usage: /decat <cat_id>"); return
    try: cid = int(context.args[0])
    except: await update.message.reply_text("❌ Number."); return
    if cid in uploaded_cats:
        del uploaded_cats[cid]
        if cid in shop_cats: shop_cats.remove(cid)
        save_data(); await update.message.reply_text(f"✅ Cat #{cid} delete!")
    else: await update.message.reply_text(f"❌ Cat #{cid} nahi mili.")

async def catlist_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID: return
    if not uploaded_cats: await update.message.reply_text("Koi cat nahi."); return
    text = f"🐱 *Cats ({len(uploaded_cats)}):*\n\n"
    for cid,cd in sorted(uploaded_cats.items()):
        text += f"ID:`{cid}` | {RARITY_NAMES.get(cd.get('rarity',12),'?')}{'  🛒' if cid in shop_cats else ''}\n"
    await update.message.reply_text(text, parse_mode="Markdown")

async def addcoupon_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID: return
    if len(context.args) < 2: await update.message.reply_text("Usage: /addcoupon <CODE> <coins> [uses]"); return
    try:
        code  = context.args[0].upper()
        coins = int(context.args[1])
        uses  = int(context.args[2]) if len(context.args)>2 else None
    except: await update.message.reply_text("❌ Sahi format."); return
    coupon_codes[code] = {"coins":coins,"uses_left":uses,"used_by":[]}; save_data()
    await update.message.reply_text(
        f"✅ Coupon!\n🎫 `{code}` | 💰 {coins} | 🔄 {uses or 'Unlimited'}", parse_mode="Markdown"
    )

async def delcoupon_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID: return
    if not context.args: await update.message.reply_text("Usage: /delcoupon <CODE>"); return
    code = context.args[0].upper()
    if code in coupon_codes:
        del coupon_codes[code]; save_data()
        await update.message.reply_text(f"✅ `{code}` delete!", parse_mode="Markdown")
    else: await update.message.reply_text(f"❌ `{code}` nahi mila.", parse_mode="Markdown")

# ══════════════════════════════════════════════════════════
#                   EXISTING COMMANDS
# ══════════════════════════════════════════════════════════

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user; chat = update.effective_chat
    users_started.add(user.id)
    if chat.type in ["group","supergroup"]: groups.add(chat.id)
    save_data()
    mention = f"[{user.first_name}](tg://user?id={user.id})"
    default = (f"*😋 Hɪᴇᴇᴇᴇᴇ {mention}*\n"
               "😉 Yᴏᴜ'ʀᴇ Tᴀʟᴋɪɴɢ Tᴏ A Cᴜᴛɪᴇ Bacchi\n\n"
               "💕 Cʜᴏᴏsᴇ Aɴ Oᴘᴛɪᴏɴ Bᴇʟᴏᴡ :")
    caption = settings.get("start_caption") or default
    photos  = settings.get("photo_list", [])
    kb      = get_welcome_keyboard()
    if photos:
        try: await update.message.reply_photo(photo=random.choice(photos)["file_id"], caption=caption, parse_mode="Markdown", reply_markup=kb); return
        except Exception as e: logger.warning(f"Start photo: {e}")
    await update.message.reply_text(default, parse_mode="Markdown", reply_markup=kb)

async def setphoto_cmd(update, context):
    if update.effective_user.id != ADMIN_ID: return
    r = update.message.reply_to_message
    if not r or not r.photo: await update.message.reply_text("❌ Photo reply mein /setphoto!"); return
    settings["photo_counter"] = settings.get("photo_counter",0)+1
    pid = settings["photo_counter"]
    settings["photo_list"].append({"id":pid,"file_id":r.photo[-1].file_id}); save_data()
    await update.message.reply_text(f"✅ Photo! ID:`{pid}` Total:{len(settings['photo_list'])}", parse_mode="Markdown")

async def photolist_cmd(update, context):
    if update.effective_user.id != ADMIN_ID: return
    p = settings.get("photo_list",[])
    if not p: await update.message.reply_text("Koi photo nahi."); return
    await update.message.reply_text("📸 *Photos:*\n"+"\n".join(f"ID:`{x['id']}`" for x in p), parse_mode="Markdown")

async def resetpic_cmd(update, context):
    if update.effective_user.id != ADMIN_ID: return
    if context.args:
        try:
            pid = int(context.args[0]); before = len(settings["photo_list"])
            settings["photo_list"] = [x for x in settings["photo_list"] if x["id"]!=pid]
            save_data()
            await update.message.reply_text(
                f"✅ ID`{pid}` hata diya!" if len(settings["photo_list"])<before else f"❌ ID`{pid}` nahi mila.",
                parse_mode="Markdown"
            )
        except: await update.message.reply_text("Usage: /resetpic <id>")
    else:
        settings["photo_list"]=[]; save_data(); await update.message.reply_text("✅ Saari photos hata di!")

async def chaton(update, context):
    if await is_admin_or_owner(update):
        chat_enabled[update.effective_chat.id]=True; await update.message.reply_text("✅ Chat ON! 😊")

async def chatoff(update, context):
    if await is_admin_or_owner(update):
        chat_enabled[update.effective_chat.id]=False; await update.message.reply_text("😴 /chaton se jagana!")

async def broadcast(update, context):
    if update.effective_user.id != ADMIN_ID: await update.message.reply_text("❌ Sirf admin!"); return
    msg = update.message; all_chats = list(users_started)+list(groups); sent=failed=0
    for cid in all_chats:
        try:
            if msg.reply_to_message: await msg.reply_to_message.copy(chat_id=cid)
            elif context.args: await context.bot.send_message(cid," ".join(context.args))
            sent+=1
        except: failed+=1
        await asyncio.sleep(0.05)
    await msg.reply_text(f"✅ Sent:{sent} Failed:{failed}")

async def setreply(update, context):
    if update.effective_user.id != ADMIN_ID: return
    msg = update.message
    if msg.reply_to_message and msg.reply_to_message.text and context.args:
        kw=msg.reply_to_message.text.strip(); rep=" ".join(context.args)
        settings["custom_replies"][kw]=rep; save_data()
        await msg.reply_text(f"✅ `{kw[:50]}` → {rep}", parse_mode="Markdown")
    elif context.args and "|" in " ".join(context.args):
        parts=" ".join(context.args).split("|",1); kw,rep=parts[0].strip(),parts[1].strip()
        if kw and rep: settings["custom_replies"][kw]=rep; save_data(); await msg.reply_text(f"✅ `{kw}` → {rep}", parse_mode="Markdown")
    else: await msg.reply_text("Usage: `/setreply keyword | jawab`", parse_mode="Markdown")

async def delreply(update, context):
    if update.effective_user.id != ADMIN_ID: return
    if not context.args: return
    kw=" ".join(context.args)
    if kw in settings["custom_replies"]:
        del settings["custom_replies"][kw]; save_data(); await update.message.reply_text(f"✅ `{kw}` delete!", parse_mode="Markdown")
    else: await update.message.reply_text(f"❌ `{kw}` nahi mila.", parse_mode="Markdown")

async def listreplies(update, context):
    if update.effective_user.id != ADMIN_ID: return
    r=settings["custom_replies"]
    if not r: await update.message.reply_text("Koi reply nahi."); return
    await update.message.reply_text("📋 *Replies:*\n\n"+"\n".join(f"`{k[:35]}` → {v[:40]}" for k,v in r.items()), parse_mode="Markdown")

async def uploadvoice_cmd(update, context):
    if update.effective_user.id != ADMIN_ID: return
    msg=update.message
    if not msg.reply_to_message: await msg.reply_text("❌ Voice reply mein /uploadVoice <keyword>!"); return
    rr=msg.reply_to_message
    fid=rr.voice.file_id if rr.voice else (rr.audio.file_id if rr.audio else None)
    if not fid: await msg.reply_text("❌ Voice/audio hona chahiye!"); return
    if not context.args: await msg.reply_text("❌ Keyword bhi do!"); return
    kw=" ".join(context.args)
    settings["voice_counter"]=settings.get("voice_counter",0)+1
    vid=str(settings["voice_counter"]); settings["voice_messages"][vid]={"file_id":fid,"keyword":kw}; save_data()
    await msg.reply_text(f"✅ Voice! ID:`{vid}` Keyword:`{kw}`", parse_mode="Markdown")

async def revoice_cmd(update, context):
    if update.effective_user.id != ADMIN_ID: return
    if not context.args: return
    vid=context.args[0]
    if vid in settings.get("voice_messages",{}):
        del settings["voice_messages"][vid]; save_data(); await update.message.reply_text(f"✅ Voice `{vid}` delete!", parse_mode="Markdown")
    else: await update.message.reply_text(f"❌ `{vid}` nahi mila.")

async def voicelist_cmd(update, context):
    if update.effective_user.id != ADMIN_ID: return
    v=settings.get("voice_messages",{})
    if not v: await update.message.reply_text("Koi voice nahi."); return
    await update.message.reply_text("🎙️ *Voices:*\n\n"+"\n".join(f"`{k}` | `{d.get('keyword','?')}`" for k,d in sorted(v.items(),key=lambda x:int(x[0]))), parse_mode="Markdown")

async def status_cmd(update, context):
    if update.effective_user.id != ADMIN_ID: return
    cap=settings.get("status_caption","Users:{users} Groups:{groups}").format(users=len(users_started),groups=len(groups))
    p=settings.get("photo_list",[])
    if p:
        try: await update.message.reply_photo(photo=random.choice(p)["file_id"],caption=cap); return
        except: pass
    await update.message.reply_text(cap)

async def setstatus_cmd(update, context):
    if update.effective_user.id != ADMIN_ID: return
    if context.args: settings["status_caption"]=" ".join(context.args); save_data(); await update.message.reply_text("✅ Status set!")

async def userlist_cmd(update, context):
    if update.effective_user.id != ADMIN_ID: return
    f=io.BytesIO(("\n".join(str(u) for u in users_started)).encode()); f.name="users.txt"
    await update.message.reply_document(f,caption=f"👥 {len(users_started)}")

async def grouplist_cmd(update, context):
    if update.effective_user.id != ADMIN_ID: return
    f=io.BytesIO(("\n".join(str(g) for g in groups)).encode()); f.name="groups.txt"
    await update.message.reply_document(f,caption=f"🌐 {len(groups)}")

async def photo_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = update.message
    if not context.args: await msg.reply_text("Usage: /photo @username"); return
    username = context.args[0].lstrip("@")
    sent = await msg.reply_photo(photo="https://files.catbox.moe/k5j9ya.jpg", caption="*😉 HYE SMILE PLEASE!! 📷📸!!*", parse_mode="Markdown")
    await asyncio.sleep(3)
    try: await sent.edit_caption(caption="*😋 Wait a Second For Image...*", parse_mode="Markdown")
    except: pass
    await asyncio.sleep(2)
    caps     = settings.get("photo_captions",[])
    cap_text = random.choice(caps)["text"] if caps else "*😉 You Are Looking So Cool!!*"
    try:
        chat_obj = await context.bot.get_chat(f"@{username}")
        photos   = await context.bot.get_user_profile_photos(chat_obj.id, limit=1)
        if photos and photos.photos:
            await msg.reply_photo(photo=photos.photos[0][-1].file_id, caption=cap_text, parse_mode="Markdown")
        else: await msg.reply_text(cap_text, parse_mode="Markdown")
    except Exception as e:
        logger.warning(f"Photo cmd: {e}"); await msg.reply_text(cap_text, parse_mode="Markdown")

async def upcaption_cmd(update, context):
    if update.effective_user.id != ADMIN_ID: return
    if not context.args: return
    settings["caption_counter"]=settings.get("caption_counter",0)+1
    cid=settings["caption_counter"]; settings["photo_captions"].append({"id":cid,"text":" ".join(context.args)}); save_data()
    await update.message.reply_text(f"✅ Caption ID:`{cid}`", parse_mode="Markdown")

async def caplist_cmd(update, context):
    if update.effective_user.id != ADMIN_ID: return
    c=settings.get("photo_captions",[])
    if not c: await update.message.reply_text("Koi caption nahi."); return
    await update.message.reply_text("📝 *Captions:*\n\n"+"\n".join(f"`{x['id']}` → _{x['text'][:55]}_" for x in c), parse_mode="Markdown")

async def dcap_cmd(update, context):
    if update.effective_user.id != ADMIN_ID: return
    if not context.args: return
    try:
        cid=int(context.args[0]); before=len(settings["photo_captions"])
        settings["photo_captions"]=[x for x in settings["photo_captions"] if x["id"]!=cid]; save_data()
        await update.message.reply_text(
            f"✅ Caption`{cid}` delete!" if len(settings["photo_captions"])<before else f"❌ ID`{cid}` nahi mila.",
            parse_mode="Markdown"
        )
    except: await update.message.reply_text("Usage: /dcap <id>")

async def gfbf_cmd(update, context):
    chat=update.effective_chat
    if chat.type not in ["group","supergroup"]: await update.message.reply_text("❌ Sirf groups mein!"); return
    if chat.id in gfbf_data and datetime.now()<gfbf_data[chat.id]["expires"]:
        d=gfbf_data[chat.id]; await update.message.reply_text(f"💑 *BF GF:*\n{d['users'][0]} & {d['users'][1]}", parse_mode="Markdown"); return
    m=list(recent_group_users.get(chat.id,set()))
    if len(m)<2: await update.message.reply_text("❌ 2 users chahiye!"); return
    sel=random.sample(m,2); gfbf_data[chat.id]={"users":sel,"expires":datetime.now()+timedelta(hours=24)}
    await update.message.reply_text(f"🌟 *TODAY'S BF GF* 🎊\n\n💑 {sel[0]} & {sel[1]}\n\nCongratulations! 🎉❤️", parse_mode="Markdown")

async def cgfbf_cmd(update, context):
    if not await is_admin_or_owner(update): return
    if not context.args or len(context.args)<2: await update.message.reply_text("Usage: /CGFBF @u1 @u2"); return
    gfbf_data[update.effective_chat.id]={"users":[context.args[0],context.args[1]],"expires":datetime.now()+timedelta(hours=24)}
    await update.message.reply_text(f"🌟 *CUSTOM BF GF*\n\n{context.args[0]} & {context.args[1]} 🎉", parse_mode="Markdown")

async def bff_cmd(update, context):
    chat=update.effective_chat
    if chat.type not in ["group","supergroup"]: await update.message.reply_text("❌ Sirf groups mein!"); return
    if chat.id in bff_data and datetime.now()<bff_data[chat.id]["expires"]:
        d=bff_data[chat.id]; await update.message.reply_text(f"👫 *BFF:* {d['users'][0]} & {d['users'][1]}!", parse_mode="Markdown"); return
    m=list(recent_group_users.get(chat.id,set()))
    if len(m)<2: await update.message.reply_text("❌ 2 users chahiye!"); return
    p=random.sample(m,2); bff_data[chat.id]={"users":p,"expires":datetime.now()+timedelta(hours=24)}
    await update.message.reply_text(f"👫 *TODAY'S BFF* 💙\n\n{p[0]} & {p[1]}\n\nGehri dosti! 🎊", parse_mode="Markdown")

async def couple_cmd(update, context):
    chat=update.effective_chat
    if chat.type not in ["group","supergroup"]: await update.message.reply_text("❌ Sirf groups mein!"); return
    m=list(recent_group_users.get(chat.id,set()))
    if len(m)<2: await update.message.reply_text("❌ 2 users chahiye!"); return
    s=random.sample(m,2); await update.message.reply_text(f"💞 *COUPLE* 💞\n\n❤️ {s[0]} & {s[1]}\n\nKitne cute! 😍", parse_mode="Markdown")

async def setcaption_cmd(update, context):
    if update.effective_user.id != ADMIN_ID: return
    if context.args: settings["start_caption"]=" ".join(context.args); save_data(); await update.message.reply_text("✅ Caption set!")

async def setbutton_cmd(update, context):
    if update.effective_user.id != ADMIN_ID: return
    if len(context.args)>=2: settings["start_buttons"][context.args[0].upper()]=context.args[1]; save_data(); await update.message.reply_text("✅ Button updated!")

async def joinvc_cmd(update, context):
    if await is_admin_or_owner(update): await update.message.reply_text("🎙️ VC join karne ki koshish!")

async def leavevc_cmd(update, context):
    if await is_admin_or_owner(update): await update.message.reply_text("👋 VC se nikal gayi!")

async def learningon_cmd(update, context):
    if update.effective_user.id != ADMIN_ID: return
    settings["ai_learning"]=True; save_data(); await update.message.reply_text("✅ AI Learning ON!")

async def learningoff_cmd(update, context):
    if update.effective_user.id != ADMIN_ID: return
    settings["ai_learning"]=False; save_data(); await update.message.reply_text("⏸️ AI Learning OFF.")

async def learnstats_cmd(update, context):
    if update.effective_user.id != ADMIN_ID: return
    await update.message.reply_text(
        f"🧠 *AI Stats:*\nStatus: {'ON ✅' if settings.get('ai_learning',True) else 'OFF ⏸️'}\n"
        f"Keywords: `{len(learned_responses)}`\nProfiles: `{len(user_profiles)}`",
        parse_mode="Markdown"
    )

async def clearlearn_cmd(update, context):
    if update.effective_user.id != ADMIN_ID: return
    learned_responses.clear(); user_profiles.clear(); conversation_history.clear(); save_data()
    await update.message.reply_text("🗑️ Learning data clear!")

async def help_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    text = (
        "📋 *Commands:*\n\n"
        "*🐱 Cat Family:*\n"
        "`/profile` — Profile + rank\n"
        "`/setfamily <naam>` — Family naam\n"
        "`/setcatname <id> <naam>` — Cat naam\n"
        "`/milk [id]` — Milk pilao (daily)\n"
        "`/store` — Shop karo\n"
        "`/sell <id>` — Cat becho\n"
        "`/gift <id>` — Gift (reply mein)\n"
        "`/daily` — 100-200 coins\n"
        "`/weekly` — 500-1000 coins\n"
        "`/coupon <code>` — Coupon redeem\n"
        "`/hclaim` — Free daily cat + bonus\n"
        "`/adop` — Spawned cat adopt\n"
        "`/top` — Top 10 cat lovers\n"
        "`/topgroups` — Top 10 groups\n\n"
        "*🎭 Fun:* `/gfbf` `/bff` `/couple` `/photo @user`\n"
        "*👮 Group Admins:* `/chaton` `/chatoff` `/cgfbf`\n"
    )
    if user.id == ADMIN_ID:
        text += (
            "\n*🔑 Bot Admin:*\n"
            "`/upload <rarity>` `/addshop <id>` `/rshop <id>` `/decat <id>` `/catlist`\n"
            "`/addcoupon CODE coins [uses]` `/delcoupon CODE`\n"
            "`/settopbanner top` `/settopbanner topgroups`\n"
            "`/broadcast` `/setphoto` `/setcaption` `/setbutton`\n"
            "`/setreply` `/delreply` `/listreplies`\n"
            "`/uploadVoice <kw>` `/revoice <id>` `/vlist`\n"
            "`/upcaption` `/caplist` `/dcap <id>`\n"
            "`/learningon` `/learningoff` `/learnstats` `/clearlearn`\n"
            "`/status` `/setstatus` `/userlist` `/grouplist`\n"
        )
    await update.message.reply_text(text, parse_mode="Markdown")

# ── MESSAGE HANDLERS ─────────────────────────────────────
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = update.message
    if not msg or not msg.text: return
    chat = update.effective_chat; user = update.effective_user
    if not user: return
    if chat.type in ["group","supergroup"]:
        groups.add(chat.id)
        recent_group_users[chat.id].add(f"[{user.first_name}](tg://user?id={user.id})")
        group_message_counter[chat.id] = group_message_counter.get(chat.id,0)+1
        if group_message_counter[chat.id] >= SPAWN_INTERVAL and chat.id not in active_spawns and uploaded_cats:
            group_message_counter[chat.id]=0; await spawn_cat(chat.id, context)
    if chat.type == "private": users_started.add(user.id)
    if not chat_enabled.get(chat.id, True): return
    custom = get_custom_reply(msg.text)
    if custom: await msg.reply_text(custom); return
    vfid = get_voice_for_text(msg.text)
    if vfid and random.random()<0.988:
        try: await msg.reply_voice(voice=vfid); return
        except Exception as e: logger.warning(f"Voice: {e}")
    try: await context.bot.send_chat_action(chat_id=chat.id, action="typing")
    except: pass
    await msg.reply_text(await get_ai_response(msg.text, get_display_name(user), user.id))

async def handle_photo_msg(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user=update.effective_user; chat=update.effective_chat
    if not user or not chat_enabled.get(chat.id,True): return
    if chat.type in ["group","supergroup"]:
        try: await context.bot.send_chat_action(chat_id=chat.id, action="typing")
        except: pass
        await update.message.reply_text(await get_ai_response("(koi cute photo bheja)", get_display_name(user), user.id))

async def handle_voice_msg(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user=update.effective_user; chat=update.effective_chat
    if not user or not chat_enabled.get(chat.id,True): return
    if chat.type in ["group","supergroup"]:
        try: await context.bot.send_chat_action(chat_id=chat.id, action="typing")
        except: pass
        await update.message.reply_text(await get_ai_response("(koi voice message bheja)", get_display_name(user), user.id))

# ── CALLBACK ROUTER ──────────────────────────────────────
async def callback_router(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    if not query: return
    d = query.data
    if   d == "noop":               await query.answer()
    elif d.startswith("family_"):   await family_callback(update, context)
    elif d.startswith("catview_"):  await catview_callback(update, context)
    elif d.startswith("closefam_"): await closefam_callback(update, context)
    elif d.startswith("adopt_"):    await adopt_callback(update, context)
    elif d.startswith("shopnav_") or d.startswith("buycat_") or d.startswith("buyitem_"):
        await store_callback(update, context)
    else: await query.answer()

# ── HANDLERS SETUP ───────────────────────────────────────
def add_handlers(app):
    # Cat Family
    app.add_handler(CommandHandler("profile",    profile_cmd))
    app.add_handler(CommandHandler("setfamily",  setfamily_cmd))
    app.add_handler(CommandHandler("setcatname", setcatname_cmd))
    app.add_handler(CommandHandler(["milk","Milk"],   milk_cmd))
    app.add_handler(CommandHandler(["store","Store"], store_cmd))
    app.add_handler(CommandHandler(["sell","Sell"],   sell_cmd))
    app.add_handler(CommandHandler(["gift","Gift"],   gift_cmd))
    app.add_handler(CommandHandler(["daily","Daily"], daily_cmd))
    app.add_handler(CommandHandler(["weekly","Weekly"], weekly_cmd))
    app.add_handler(CommandHandler(["coupon","Coupon"], coupon_cmd))
    app.add_handler(CommandHandler(["hclaim","Hclaim"], hclaim_cmd))
    app.add_handler(CommandHandler(["adop","Adop"],   adop_cmd))
    app.add_handler(CommandHandler(["top","Top"],     top_cmd))
    app.add_handler(CommandHandler(["topgroups","Topgroups"], topgroups_cmd))
    # Admin cat
    app.add_handler(CommandHandler(["upload","Upload"], upload_cat_cmd))
    app.add_handler(CommandHandler("addshop",      addshop_cmd))
    app.add_handler(CommandHandler("rshop",        rshop_cmd))
    app.add_handler(CommandHandler("decat",        decat_cmd))
    app.add_handler(CommandHandler("catlist",      catlist_cmd))
    app.add_handler(CommandHandler("addcoupon",    addcoupon_cmd))
    app.add_handler(CommandHandler("delcoupon",    delcoupon_cmd))
    app.add_handler(CommandHandler("settopbanner", settopbanner_cmd))
    # Existing
    app.add_handler(CommandHandler("start",    start))
    app.add_handler(CommandHandler("help",     help_cmd))
    app.add_handler(CommandHandler(["chaton","CHATON"],   chaton))
    app.add_handler(CommandHandler(["chatoff","CHATOFF"], chatoff))
    app.add_handler(CommandHandler(["broadcast","bcast"], broadcast))
    app.add_handler(CommandHandler(["gfbf","GFBF"],     gfbf_cmd))
    app.add_handler(CommandHandler(["cgfbf","CGFBF"],   cgfbf_cmd))
    app.add_handler(CommandHandler(["bff","BFF"],       bff_cmd))
    app.add_handler(CommandHandler(["couple","COUPLE"], couple_cmd))
    app.add_handler(CommandHandler("setcaption",  setcaption_cmd))
    app.add_handler(CommandHandler("setbutton",   setbutton_cmd))
    app.add_handler(CommandHandler(["setreply","Setreply"],     setreply))
    app.add_handler(CommandHandler(["delreply","Delreply"],     delreply))
    app.add_handler(CommandHandler(["listreplies","Listreplies"], listreplies))
    app.add_handler(CommandHandler(["setphoto","addphoto"],     setphoto_cmd))
    app.add_handler(CommandHandler("photolist",   photolist_cmd))
    app.add_handler(CommandHandler("resetpic",    resetpic_cmd))
    app.add_handler(CommandHandler(["uploadVoice","uploadvoice"], uploadvoice_cmd))
    app.add_handler(CommandHandler(["revoice","Revoice"],         revoice_cmd))
    app.add_handler(CommandHandler(["vlist","voicelist"],         voicelist_cmd))
    app.add_handler(CommandHandler(["status","Status"],   status_cmd))
    app.add_handler(CommandHandler("setstatus",   setstatus_cmd))
    app.add_handler(CommandHandler("userlist",    userlist_cmd))
    app.add_handler(CommandHandler("grouplist",   grouplist_cmd))
    app.add_handler(CommandHandler(["photo","Photo"], photo_cmd))
    app.add_handler(CommandHandler("upcaption",   upcaption_cmd))
    app.add_handler(CommandHandler("caplist",     caplist_cmd))
    app.add_handler(CommandHandler("dcap",        dcap_cmd))
    app.add_handler(CommandHandler(["joinvc","jvc"],   joinvc_cmd))
    app.add_handler(CommandHandler(["leavevc","lvc"],  leavevc_cmd))
    app.add_handler(CommandHandler("learningon",  learningon_cmd))
    app.add_handler(CommandHandler("learningoff", learningoff_cmd))
    app.add_handler(CommandHandler("learnstats",  learnstats_cmd))
    app.add_handler(CommandHandler("clearlearn",  clearlearn_cmd))
    app.add_handler(CallbackQueryHandler(callback_router))
    app.add_handler(MessageHandler(filters.PHOTO, handle_photo_msg))
    app.add_handler(MessageHandler(filters.VOICE | filters.AUDIO, handle_voice_msg))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

if __name__ == "__main__":
    load_data()
    app = ApplicationBuilder().token(BOT_TOKEN).build()
    add_handlers(app)
    logger.info("✅ Sinzhu Bot — Full System Online!")
    app.run_polling(drop_pending_updates=True)
