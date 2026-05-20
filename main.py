import os
import random
import math
import asyncio
from datetime import datetime, date, timedelta
from dotenv import load_dotenv

from telegram import (
    Update, InlineKeyboardButton, InlineKeyboardMarkup
)
from telegram.ext import (
    Application, CommandHandler, MessageHandler,
    CallbackQueryHandler, ContextTypes, filters
)

import database as db
import admin as adm
from keyboards import (
    main_menu_keyboard, harem_keyboard, waifu_detail_keyboard,
    sell_confirm_keyboard, shop_keyboard, buy_confirm_keyboard,
    top_keyboard, rank_keyboard, WAIFU_PER_PAGE
)
from waifu_data import RARITY_TIERS, RARITY_NUMBER_MAP, RANK_SYSTEM, get_rank

load_dotenv()
BOT_TOKEN = os.getenv("BOT_TOKEN")
ADMIN_IDS = [int(x) for x in os.getenv("ADMIN_IDS", "123456789").split(",")]

# ─── HELPERS ──────────────────────────────────────────────

def get_display_name(user):
    return f"@{user.username}" if user.username else user.first_name

def paginate(items, page, per_page):
    total = math.ceil(len(items) / per_page) if items else 1
    page = max(1, min(page, total))
    start = (page - 1) * per_page
    return items[start:start + per_page], total

async def spawn_waifu(context: ContextTypes.DEFAULT_TYPE, chat_id: int):
    waifus = db.get_all_waifus()
    if not waifus:
        return

    weights = [RARITY_TIERS.get(w["rarity"], {}).get("weight", 50) for w in waifus]
    chosen = random.choices(waifus, weights=weights, k=1)[0]

    db.update_group(chat_id, current_waifu_id=chosen["id"], current_waifu_claimed=0)
    db.update_group(chat_id, total_spawns=db.get_group(chat_id)["total_spawns"] + 1)

    caption = (
        f"A New {chosen['rarity']} SealWaifu\U0001f4ab Appeared...\n"
        f"/Clutch {chosen['name']} and add in Your SealWaifu Collection \U0001f47e"
    )

    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton(f"\U0001f3f9 Clutch {chosen['name']}", callback_data=f"quick_hunt_{chosen['id']}")]
    ])

    try:
        if chosen.get("file_id"):
            await context.bot.send_photo(
                chat_id=chat_id,
                photo=chosen["file_id"],
                caption=caption,
                reply_markup=keyboard
            )
        elif chosen.get("image_url"):
            await context.bot.send_photo(
                chat_id=chat_id,
                photo=chosen["image_url"],
                caption=caption,
                reply_markup=keyboard
            )
        else:
            await context.bot.send_message(
                chat_id=chat_id,
                text=caption,
                reply_markup=keyboard
            )
    except Exception as e:
        print(f"Spawn error: {e}")

# ─── /start ───────────────────────────────────────────────

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    db.get_user(user.id, user.username, user.first_name)

    welcome_photo = db.get_setting("welcome_photo", "")
    welcome_caption = db.get_setting(
        "welcome_caption",
        f"Hlw kese ho \U0001f338\n\nWelcome to **Sinzhu Waifu Bot**!\nCollect anime waifus, earn Onex, and become the top Shinobi! \U0001f3af"
    )
    welcome_link = db.get_setting("welcome_link", "https://t.me/Main_Clutch")

    top_groups = db.get_top_groups(5)
    top_btns = []
    for g in top_groups:
        title = g["chat_title"] or str(g["chat_id"])
        top_btns.append(InlineKeyboardButton(title, url=f"https://t.me/c/{str(g['chat_id']).replace('-100','')}"))

    kb_rows = [
        [
            InlineKeyboardButton("\U0001f4cb Commands", callback_data="show_commands"),
            InlineKeyboardButton("\U0001f44b Welcome", url=welcome_link),
        ],
        [
            InlineKeyboardButton("\U0001f3c6 Top Groups", callback_data="top_groups_btn"),
            InlineKeyboardButton("\U0001f451 Owner", url="https://t.me/OwnerSween"),
        ],
    ]
    keyboard = InlineKeyboardMarkup(kb_rows)

    try:
        if welcome_photo:
            await update.message.reply_photo(
                photo=welcome_photo,
                caption=welcome_caption,
                reply_markup=keyboard,
                parse_mode="Markdown"
            )
        else:
            await update.message.reply_text(
                welcome_caption,
                reply_markup=keyboard,
                parse_mode="Markdown"
            )
    except Exception:
        await update.message.reply_text(
            welcome_caption,
            reply_markup=keyboard,
            parse_mode="Markdown"
        )

# ─── /Clutch (Hunt) ───────────────────────────────────────

async def clutch_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_chat.type == "private":
        await update.message.reply_text("\u274c Clutch only works in group chats!")
        return

    user = update.effective_user
    args = context.args
    if not args:
        await update.message.reply_text("Usage: `/Clutch <waifu name>`", parse_mode="Markdown")
        return

    name = " ".join(args).strip()
    group = db.get_group(update.effective_chat.id)

    if not group["current_waifu_id"]:
        await update.message.reply_text("\U0001f634 No waifu has spawned yet! Wait for one...")
        return
    if group["current_waifu_claimed"]:
        await update.message.reply_text("\U0001f4a8 Too slow! That waifu was already claimed.")
        return

    waifu = db.get_waifu_by_id(group["current_waifu_id"])
    if not waifu:
        await update.message.reply_text("\u274c Waifu not found.")
        return

    if name.lower() != waifu["name"].lower().replace("-", " "):
        hint = waifu["name"][0]
        await update.message.reply_text(
            f"\u274c Wrong name! Hint: starts with **{hint}**...",
            parse_mode="Markdown"
        )
        return

    db.update_group(update.effective_chat.id, current_waifu_claimed=1)
    db.get_user(user.id, user.username, user.first_name)
    db.give_waifu_to_user(user.id, waifu["id"])

    rarity_data = RARITY_TIERS.get(waifu["rarity"], {})
    bonus_onex = rarity_data.get("sell_price", 50) // 5
    u = db.get_user(user.id)
    db.update_user(user.id, onex=u["onex"] + bonus_onex)

    text = (
        f"\U0001f389 **{get_display_name(user)} caught {waifu['name']}!**\n\n"
        f"\u2b50 Rarity: {waifu['rarity']}\n"
        f"\U0001f4fa Anime: {waifu['anime']}\n"
        f"\U0001f4b0 Bonus: +{bonus_onex} Onex\n\n"
        f"Use `/Harem` to view your collection!"
    )
    keyboard = InlineKeyboardMarkup([
        [
            InlineKeyboardButton("\U0001f3b4 View Harem", callback_data="harem_1"),
            InlineKeyboardButton("\U0001f4b0 Balance", callback_data="balance"),
        ]
    ])
    await update.message.reply_text(text, reply_markup=keyboard, parse_mode="Markdown")

# ─── /Harem ───────────────────────────────────────────────

async def harem_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    db.get_user(user.id, user.username, user.first_name)
    waifus = db.get_user_waifus(user.id)

    if not waifus:
        kb = InlineKeyboardMarkup([[InlineKeyboardButton("\U0001f519 Main Menu", callback_data="main_menu")]])
        await update.message.reply_text(
            "\U0001f494 Your harem is empty! Go clutch some waifus in a group!",
            reply_markup=kb
        )
        return

    page = 1
    chunk, total_pages = paginate(waifus, page, WAIFU_PER_PAGE)
    u_data = db.get_user(user.id)

    text = f"\U0001f3b4 **{user.first_name}'s Harem** ({len(waifus)} waifus)\n\n"
    for w in chunk:
        fav_star = " \u2b50" if u_data.get("favorite_waifu_id") == w["id"] else ""
        text += f"\u2022 {w['rarity']} **{w['name']}** \u2014 {w['anime']}{fav_star} [ID:{w['id']}]\n"

    await update.message.reply_text(
        text,
        reply_markup=harem_keyboard(chunk, page, total_pages, user.id),
        parse_mode="Markdown"
    )

# ─── /Hclaim ──────────────────────────────────────────────

async def hclaim_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    u = db.get_user(user.id, user.username, user.first_name)
    today = date.today().isoformat()

    if u["hclaim_date"] == today:
        kb = InlineKeyboardMarkup([[InlineKeyboardButton("\U0001f3b4 View Harem", callback_data="harem_1")]])
        await update.message.reply_text("\u23f0 Free waifu already claimed today! Come back tomorrow.", reply_markup=kb)
        return

    waifus = db.get_all_waifus()
    if not waifus:
        await update.message.reply_text("\u274c No waifus in database yet!")
        return

    low_rarities = [w for w in waifus if w["rarity"] in list(RARITY_TIERS.keys())[:5]]
    w = random.choice(low_rarities if low_rarities else waifus)

    db.give_waifu_to_user(user.id, w["id"])
    db.update_user(user.id, hclaim_date=today)

    kb = InlineKeyboardMarkup([
        [
            InlineKeyboardButton("\U0001f3b4 View Harem", callback_data="harem_1"),
            InlineKeyboardButton("\U0001f519 Menu", callback_data="main_menu"),
        ]
    ])
    await update.message.reply_text(
        f"\U0001f381 **Free Daily Waifu!**\n\n\U0001f3b4 {w['name']} ({w['rarity']}) added to your harem!",
        reply_markup=kb,
        parse_mode="Markdown"
    )

# ─── /Onex ────────────────────────────────────────────────

async def onex_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    u = db.get_user(user.id, user.username, user.first_name)
    kb = InlineKeyboardMarkup([
        [
            InlineKeyboardButton("\U0001f4e6 Daily", callback_data="daily"),
            InlineKeyboardButton("\U0001f6d2 Store", callback_data="shop_1"),
        ]
    ])
    await update.message.reply_text(
        f"\U0001f4b0 **{user.first_name}'s Balance**\n\n\U0001f48e Onex: `{u['onex']}`",
        reply_markup=kb,
        parse_mode="Markdown"
    )

# ─── /Daily ───────────────────────────────────────────────

async def daily_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    u = db.get_user(user.id, user.username, user.first_name)
    today = date.today().isoformat()

    if u["daily_claim"] == today:
        tomorrow = (date.today() + timedelta(days=1)).strftime("%d %b")
        kb = InlineKeyboardMarkup([[InlineKeyboardButton("\U0001f519 Back", callback_data="main_menu")]])
        await update.message.reply_text(
            f"\u23f0 Already claimed today! Come back tomorrow ({tomorrow}).",
            reply_markup=kb
        )
        return

    reward = random.randint(200, 500)
    db.update_user(user.id, onex=u["onex"] + reward, daily_claim=today)
    kb = InlineKeyboardMarkup([
        [
            InlineKeyboardButton("\U0001f4b0 Check Balance", callback_data="balance"),
            InlineKeyboardButton("\U0001f31f Weekly", callback_data="welkin"),
        ]
    ])
    await update.message.reply_text(
        f"\u2705 **Daily Reward Claimed!**\n\n\U0001f4b0 +{reward} Onex\n\U0001f48e Balance: {u['onex']+reward} Onex",
        reply_markup=kb,
        parse_mode="Markdown"
    )

# ─── /Weakly (Weekly) ─────────────────────────────────────

async def weekly_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    u = db.get_user(user.id, user.username, user.first_name)
    today = date.today().isoformat()

    if u["welkin_claim"] == today:
        kb = InlineKeyboardMarkup([[InlineKeyboardButton("\U0001f519 Back", callback_data="main_menu")]])
        await update.message.reply_text("\u23f0 Weekly already claimed today! Come back tomorrow.", reply_markup=kb)
        return

    reward = 1000
    db.update_user(user.id, onex=u["onex"] + reward, welkin_claim=today)
    kb = InlineKeyboardMarkup([
        [
            InlineKeyboardButton("\U0001f4b0 Balance", callback_data="balance"),
            InlineKeyboardButton("\U0001f4e6 Daily", callback_data="daily"),
        ]
    ])
    await update.message.reply_text(
        f"\U0001f31f **Weekly Gold!**\n\n\U0001f4b0 +{reward} Onex",
        reply_markup=kb,
        parse_mode="Markdown"
    )

# ─── /Tresure ─────────────────────────────────────────────

async def treasure_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    u = db.get_user(user.id, user.username, user.first_name)

    result = random.choices(["onex", "waifu", "nothing"], weights=[50, 30, 20], k=1)[0]

    if result == "onex":
        amount = random.randint(100, 1000)
        db.update_user(user.id, onex=u["onex"] + amount)
        text = f"\U0001f48e **Treasure Opened!**\n\n\U0001f381 You found **{amount} Onex**!"
    elif result == "waifu":
        waifus = db.get_all_waifus()
        if waifus:
            w = random.choice(waifus)
            db.give_waifu_to_user(user.id, w["id"])
            text = f"\U0001f48e **Treasure Opened!**\n\n\U0001f3b4 You found **{w['name']}** ({w['rarity']})!"
        else:
            text = "\U0001f48e **Treasure Opened!**\n\nThe chest was empty... \U0001f622"
    else:
        text = "\U0001f48e **Treasure Opened!**\n\nBetter luck next time! \U0001f622"

    kb = InlineKeyboardMarkup([[InlineKeyboardButton("\U0001f519 Menu", callback_data="main_menu")]])
    await update.message.reply_text(text, reply_markup=kb, parse_mode="Markdown")

# ─── /Wsell ───────────────────────────────────────────────

async def wsell_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    if not context.args:
        await update.message.reply_text("Usage: `/Wsell <harem_id>`", parse_mode="Markdown")
        return
    try:
        uw_id = int(context.args[0])
    except Exception:
        await update.message.reply_text("\u274c Invalid ID!")
        return

    waifu = db.get_waifu_by_uw_id(uw_id)
    if not waifu or waifu["user_id"] != user.id:
        await update.message.reply_text("\u274c Waifu not found in your harem!")
        return

    rarity_data = RARITY_TIERS.get(waifu["rarity"], {})
    sell_price = rarity_data.get("sell_price", 50)

    await update.message.reply_text(
        f"\U0001f4b8 Sell **{waifu['name']}** for {sell_price} Onex?",
        reply_markup=sell_confirm_keyboard(uw_id, sell_price),
        parse_mode="Markdown"
    )

# ─── /Gift ────────────────────────────────────────────────

async def gift_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    if not update.message.reply_to_message:
        await update.message.reply_text("\u274c Reply to someone's message to gift them a waifu!")
        return
    if not context.args:
        await update.message.reply_text("Usage: `/Gift <harem_id>` (reply to user)", parse_mode="Markdown")
        return
    try:
        uw_id = int(context.args[0])
    except Exception:
        await update.message.reply_text("\u274c Invalid ID!")
        return

    waifu = db.get_waifu_by_uw_id(uw_id)
    if not waifu or waifu["user_id"] != user.id:
        await update.message.reply_text("\u274c Waifu not in your harem!")
        return

    target = update.message.reply_to_message.from_user
    if target.id == user.id:
        await update.message.reply_text("\u274c Can't gift yourself!")
        return

    db.remove_user_waifu(uw_id, user.id)
    db.get_user(target.id, target.username, target.first_name)
    db.give_waifu_to_user(target.id, waifu["waifu_id"])

    await update.message.reply_text(
        f"\U0001f381 **Gift Sent!**\n\n"
        f"{get_display_name(user)} gifted **{waifu['name']}** to {get_display_name(target)}!",
        parse_mode="Markdown"
    )

# ─── /Store ───────────────────────────────────────────────

async def store_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    waifus = db.get_shop_waifus()
    if not waifus:
        await update.message.reply_text("\U0001f6d2 Store is empty! Admin hasn't added waifus yet.")
        return
    page = 1
    chunk, total_pages = paginate(waifus, page, WAIFU_PER_PAGE)
    await update.message.reply_text(
        f"\U0001f6d2 **Waifu Store** (Page {page}/{total_pages})\n\nSelect a waifu to buy:",
        reply_markup=shop_keyboard(chunk, page, total_pages),
        parse_mode="Markdown"
    )

# ─── /Ranks ───────────────────────────────────────────────

async def ranks_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    u = db.get_user(user.id, user.username, user.first_name)
    waifu_count = u["total_waifus"]

    current_rank, next_rank, next_min = get_rank(waifu_count)
    needed = (next_min - waifu_count) if next_min else 0

    text = (
        f"\U0001f340 **{user.first_name} Rank Card** \U0001f3f7\n"
        f"\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\n"
        f"\U0001f52e Rank: {current_rank}\n"
        f"\U0001f3b4 Waifus Collected: {waifu_count}\n"
    )
    if next_rank:
        text += f"\U0001f51c Next Rank: {next_rank} ({needed} more needed)\n"
    else:
        text += "\U0001f451 You are at the highest rank — **Grand Master**!\n"

    kb = InlineKeyboardMarkup([
        [
            InlineKeyboardButton("\U0001f3c6 Top Collectors", callback_data="top"),
            InlineKeyboardButton("\U0001f519 Menu", callback_data="main_menu"),
        ]
    ])
    await update.message.reply_text(text, reply_markup=kb, parse_mode="Markdown")

# ─── /TopChat ─────────────────────────────────────────────

async def topchat_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    top_users = db.get_top_collectors(10)
    top_groups = db.get_top_groups(10)

    text = "\U0001f3c6 **Top 10 Shinobi** (Most Waifus)\n\n"
    medals = ["\U0001f947", "\U0001f948", "\U0001f949"] + ["\U0001f539"] * 7
    for i, u in enumerate(top_users):
        name = f"@{u['username']}" if u["username"] else u["first_name"]
        text += f"{medals[i]} {name} \u2014 {u['total_waifus']} waifus\n"

    text += "\n\U0001f3d8 **Top 10 Villages** (Most Spawns)\n\n"
    for i, g in enumerate(top_groups):
        title = g["chat_title"] or str(g["chat_id"])
        text += f"{medals[i]} {title} \u2014 {g['total_spawns']} spawns\n"

    kb = InlineKeyboardMarkup([[InlineKeyboardButton("\U0001f519 Menu", callback_data="main_menu")]])
    await update.message.reply_text(text, reply_markup=kb, parse_mode="Markdown")

# ─── /Redeem ──────────────────────────────────────────────

async def redeem_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    if not context.args:
        await update.message.reply_text(
            "\U0001f3ab Usage: `/Redeem <code>`\n\nExample: `/Redeem SINZHU100`",
            parse_mode="Markdown"
        )
        return

    code = context.args[0].strip()
    onex_reward, error = db.use_redeem_code(code, user.id)

    if error:
        await update.message.reply_text(error)
        return

    u = db.get_user(user.id)
    db.update_user(user.id, onex=u["onex"] + onex_reward)

    kb = InlineKeyboardMarkup([[InlineKeyboardButton("\U0001f4b0 Check Balance", callback_data="balance")]])
    await update.message.reply_text(
        f"\u2705 **Code Redeemed!**\n\n\U0001f4b0 +{onex_reward} Onex added!",
        reply_markup=kb,
        parse_mode="Markdown"
    )

# ─── /Slavetime ───────────────────────────────────────────

async def slavetime_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_chat.type == "private":
        await update.message.reply_text("\u274c This command only works in groups!")
        return

    user = update.effective_user
    if not adm.is_admin(user.id):
        await update.message.reply_text("\u274c Admin only command!")
        return

    if not context.args:
        g = db.get_group(update.effective_chat.id)
        await update.message.reply_text(
            f"\u23f0 Current spawn interval: **{g['spawn_interval']} messages**\n\nUsage: `/Slavetime <number>` (min: 5)",
            parse_mode="Markdown"
        )
        return

    try:
        interval = int(context.args[0])
        assert interval >= 5
    except Exception:
        await update.message.reply_text("\u274c Invalid! Minimum is 5 messages.")
        return

    db.update_group(update.effective_chat.id, spawn_interval=interval)
    await update.message.reply_text(
        f"\u2705 Waifu spawn interval set to **{interval} messages**!",
        parse_mode="Markdown"
    )

# ─── Admin Upload ─────────────────────────────────────────

async def upload_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    if not adm.is_admin(user.id):
        await update.message.reply_text("\u274c Admin only!")
        return

    msg = update.message
    if not msg.reply_to_message or not msg.reply_to_message.photo:
        await update.message.reply_text(
            "\U0001f4f8 Reply to a **photo** with:\n`/Upload name anime rarity_number`\n\nExample:\n`/Upload muzan-kibutsuji Demon-Slayer 3`\n\nRarities:\n1=\U0001f315 MoOnLie  2=\u2728 SaSui  3=\U0001f525 EnYire\n4=\U0001f341 HIssoin  5=\U0001f33f LieHien  6=\U0001f4b8 Billionaire\n7=\U0001f98b SeeWa  8=\U0001f48b ConConHie  9=\U0001f337 GrownBie\n10=\U0001f9da EraBie  11=\U0001f344 Natural  12=\U0001f52e MOnSee\n13=\U0001f324 SunShine  14=\u26c8 TunDie  15=\U0001f30d EarthEie",
            parse_mode="Markdown"
        )
        return

    if len(context.args) < 3:
        await update.message.reply_text(
            "Usage: `/Upload <name> <anime> <rarity_number>`",
            parse_mode="Markdown"
        )
        return

    name = context.args[0].replace("-", " ")
    anime = context.args[1].replace("-", " ")
    try:
        rarity_num = int(context.args[2])
        rarity = RARITY_NUMBER_MAP.get(rarity_num)
        if not rarity:
            raise ValueError()
    except Exception:
        await update.message.reply_text("\u274c Invalid rarity number! Use 1-15.")
        return

    photo = msg.reply_to_message.photo[-1]
    file_id = photo.file_id

    wid = db.add_waifu(name, anime, rarity, file_id=file_id, added_by=user.id)

    await update.message.reply_text(
        f"\u2705 **Waifu Uploaded!**\n\n\U0001f3b4 {name}\n\U0001f4fa {anime}\n\u2b50 {rarity}\n\U0001f194 ID: {wid}",
        parse_mode="Markdown"
    )

async def adsh_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    if not adm.is_admin(user.id):
        await update.message.reply_text("\u274c Admin only!")
        return
    if not context.args:
        await update.message.reply_text("Usage: `/Adsh <waifu_id>`", parse_mode="Markdown")
        return
    try:
        wid = int(context.args[0])
    except Exception:
        await update.message.reply_text("\u274c Invalid ID!")
        return

    conn = db.get_conn()
    conn.execute("UPDATE waifus SET in_shop=1 WHERE id=?", (wid,))
    conn.commit()
    conn.close()
    await update.message.reply_text(f"\u2705 Waifu ID {wid} added to shop!")

async def remove_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    if not adm.is_admin(user.id):
        await update.message.reply_text("\u274c Admin only!")
        return
    if not context.args:
        await update.message.reply_text("Usage: `/Remove <waifu_id>`", parse_mode="Markdown")
        return
    try:
        wid = int(context.args[0])
    except Exception:
        await update.message.reply_text("\u274c Invalid ID!")
        return

    conn = db.get_conn()
    conn.execute("UPDATE waifus SET in_shop=0 WHERE id=?", (wid,))
    conn.commit()
    conn.close()
    await update.message.reply_text(f"\u2705 Waifu ID {wid} removed from shop!")

async def give_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    if not adm.is_admin(user.id):
        await update.message.reply_text("\u274c Admin only!")
        return
    if len(context.args) < 2:
        await update.message.reply_text("Usage: `/Give <user_id> <waifu_id>`", parse_mode="Markdown")
        return
    try:
        target_id = int(context.args[0])
        wid = int(context.args[1])
    except Exception:
        await update.message.reply_text("\u274c Invalid arguments!")
        return

    waifu = db.get_waifu_by_id(wid)
    if not waifu:
        await update.message.reply_text("\u274c Waifu not found!")
        return

    db.get_user(target_id)
    db.give_waifu_to_user(target_id, wid)
    await update.message.reply_text(f"\u2705 Gave **{waifu['name']}** to user `{target_id}`!", parse_mode="Markdown")

async def creddem_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    if not adm.is_admin(user.id):
        await update.message.reply_text("\u274c Admin only!")
        return
    if len(context.args) < 3:
        await update.message.reply_text(
            "Usage: `/Creddem <code> <onex> <uses>`\n\nExample: `/Creddem SINZHU100 500 10`",
            parse_mode="Markdown"
        )
        return
    code = context.args[0].upper()
    try:
        onex = int(context.args[1])
        uses = int(context.args[2])
    except Exception:
        await update.message.reply_text("\u274c Invalid values!")
        return

    db.create_redeem_code(code, onex, uses, user.id)
    await update.message.reply_text(
        f"\u2705 **Redeem Code Created!**\n\n\U0001f3ab Code: `{code}`\n\U0001f4b0 Onex: {onex}\n\U0001f504 Uses: {uses}",
        parse_mode="Markdown"
    )

async def broadcast_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    if not adm.is_admin(user.id):
        await update.message.reply_text("\u274c Admin only!")
        return
    if not update.message.reply_to_message:
        await update.message.reply_text("Reply to a message with /Broadcast to send it to all users.")
        return

    users = db.get_all_users()
    success = 0
    for u in users:
        try:
            await context.bot.forward_message(
                chat_id=u["user_id"],
                from_chat_id=update.effective_chat.id,
                message_id=update.message.reply_to_message.message_id
            )
            success += 1
        except Exception:
            pass
        await asyncio.sleep(0.05)

    await update.message.reply_text(f"\u2705 Broadcast sent to {success}/{len(users)} users.")

async def setphoto_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    if not adm.is_admin(user.id):
        await update.message.reply_text("\u274c Admin only!")
        return
    if not context.args:
        await update.message.reply_text("Usage: `/Setphoto <image_url>`", parse_mode="Markdown")
        return
    url = context.args[0]
    db.set_setting("welcome_photo", url)
    await update.message.reply_text("\u2705 Welcome photo updated!")

async def removephoto_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    if not adm.is_admin(user.id):
        await update.message.reply_text("\u274c Admin only!")
        return
    db.set_setting("welcome_photo", "")
    await update.message.reply_text("\u2705 Welcome photo removed!")

async def setcaption_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    if not adm.is_admin(user.id):
        await update.message.reply_text("\u274c Admin only!")
        return
    if not context.args:
        await update.message.reply_text("Usage: `/Setcaption <text>`", parse_mode="Markdown")
        return
    caption = " ".join(context.args)
    db.set_setting("welcome_caption", caption)
    await update.message.reply_text("\u2705 Welcome caption updated!")

async def changebtn_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    if not adm.is_admin(user.id):
        await update.message.reply_text("\u274c Admin only!")
        return
    if not context.args:
        await update.message.reply_text(
            "Usage: `/ChangeButton <welcome_link>`\n\nExample: `/ChangeButton https://t.me/Main_Clutch`",
            parse_mode="Markdown"
        )
        return
    link = context.args[0]
    db.set_setting("welcome_link", link)
    await update.message.reply_text("\u2705 Button link updated!")

async def glist_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    if not adm.is_admin(user.id):
        await update.message.reply_text("\u274c Admin only!")
        return
    groups = db.get_all_groups()
    text = f"\U0001f4cb **Group List** ({len(groups)} groups)\n\n"
    for g in groups[:30]:
        text += f"\u2022 {g['chat_title'] or g['chat_id']} \u2014 {g['total_spawns']} spawns\n"
    await update.message.reply_text(text, parse_mode="Markdown")

async def mlist_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    if not adm.is_admin(user.id):
        await update.message.reply_text("\u274c Admin only!")
        return
    users = db.get_all_users()
    text = f"\U0001f465 **User List** ({len(users)} users)\n\n"
    for u in users[:30]:
        name = f"@{u['username']}" if u["username"] else u["first_name"]
        text += f"\u2022 {name} \u2014 {u['total_waifus']} waifus\n"
    await update.message.reply_text(text, parse_mode="Markdown")

# ─── MESSAGE HANDLER ──────────────────────────────────────

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message or not update.effective_chat:
        return

    msg = update.message
    chat = update.effective_chat
    user = update.effective_user

    if chat.type == "private":
        # Admin state handlers
        text = msg.text or ""
        state = context.user_data.get("admin_state")

        if state == "awaiting_code":
            parts = text.strip().split()
            if len(parts) == 3:
                code, onex_str, uses_str = parts
                try:
                    db.create_redeem_code(code.upper(), int(onex_str), int(uses_str), user.id)
                    context.user_data.pop("admin_state", None)
                    kb = InlineKeyboardMarkup([[InlineKeyboardButton("\U0001f519 Admin", callback_data="back_admin")]])
                    await msg.reply_text(
                        f"\u2705 Code `{code.upper()}` created! {onex_str} Onex, {uses_str} uses.",
                        reply_markup=kb, parse_mode="Markdown"
                    )
                except Exception:
                    await msg.reply_text("\u274c Error creating code. Format: `CODE ONEX USES`", parse_mode="Markdown")
            else:
                await msg.reply_text("\u274c Format: `CODE ONEX USES`", parse_mode="Markdown")
            return

        if state == "awaiting_welcome_photo":
            db.set_setting("welcome_photo", text.strip())
            context.user_data.pop("admin_state", None)
            kb = InlineKeyboardMarkup([[InlineKeyboardButton("\U0001f519 Admin", callback_data="back_admin")]])
            await msg.reply_text("\u2705 Welcome photo updated!", reply_markup=kb)
            return

        if state == "awaiting_welcome_caption":
            db.set_setting("welcome_caption", text.strip())
            context.user_data.pop("admin_state", None)
            kb = InlineKeyboardMarkup([[InlineKeyboardButton("\U0001f519 Admin", callback_data="back_admin")]])
            await msg.reply_text("\u2705 Welcome caption updated!", reply_markup=kb)
            return

        if state == "awaiting_button_change":
            parts = text.strip().split()
            if parts:
                db.set_setting("welcome_link", parts[0])
                context.user_data.pop("admin_state", None)
                kb = InlineKeyboardMarkup([[InlineKeyboardButton("\U0001f519 Admin", callback_data="back_admin")]])
                await msg.reply_text("\u2705 Button link updated!", reply_markup=kb)
            else:
                await msg.reply_text("\u274c Send a valid URL.")
            return

        if state == "awaiting_give_waifu":
            parts = text.strip().split()
            if len(parts) == 2:
                try:
                    target_id, wid = int(parts[0]), int(parts[1])
                    waifu = db.get_waifu_by_id(wid)
                    if waifu:
                        db.get_user(target_id)
                        db.give_waifu_to_user(target_id, wid)
                        context.user_data.pop("admin_state", None)
                        kb = InlineKeyboardMarkup([[InlineKeyboardButton("\U0001f519 Admin", callback_data="back_admin")]])
                        await msg.reply_text(f"\u2705 Gave {waifu['name']} to user {target_id}!", reply_markup=kb)
                    else:
                        await msg.reply_text("\u274c Waifu not found!")
                except Exception:
                    await msg.reply_text("\u274c Format: `USER_ID WAIFU_ID`", parse_mode="Markdown")
            else:
                await msg.reply_text("\u274c Format: `USER_ID WAIFU_ID`", parse_mode="Markdown")
            return

        if state == "awaiting_adsh":
            try:
                wid = int(text.strip())
                conn = db.get_conn()
                conn.execute("UPDATE waifus SET in_shop=1 WHERE id=?", (wid,))
                conn.commit()
                conn.close()
                context.user_data.pop("admin_state", None)
                kb = InlineKeyboardMarkup([[InlineKeyboardButton("\U0001f519 Admin", callback_data="back_admin")]])
                await msg.reply_text(f"\u2705 Waifu {wid} added to shop!", reply_markup=kb)
            except Exception:
                await msg.reply_text("\u274c Send a valid waifu ID.")
            return

        if state == "awaiting_removeshop":
            try:
                wid = int(text.strip())
                conn = db.get_conn()
                conn.execute("UPDATE waifus SET in_shop=0 WHERE id=?", (wid,))
                conn.commit()
                conn.close()
                context.user_data.pop("admin_state", None)
                kb = InlineKeyboardMarkup([[InlineKeyboardButton("\U0001f519 Admin", callback_data="back_admin")]])
                await msg.reply_text(f"\u2705 Waifu {wid} removed from shop!", reply_markup=kb)
            except Exception:
                await msg.reply_text("\u274c Send a valid waifu ID.")
            return

        return

    # Group message handling
    db.get_user(user.id, user.username, user.first_name)
    group = db.get_group(chat.id, chat.title)
    new_count = group["message_count"] + 1
    spawn_interval = group["spawn_interval"] or 15

    if new_count >= spawn_interval:
        db.update_group(chat.id, message_count=0)
        await spawn_waifu(context, chat.id)
    else:
        db.update_group(chat.id, message_count=new_count)

# ─── CALLBACK HANDLER ─────────────────────────────────────

async def handle_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    user = query.from_user
    data = query.data

    if data.startswith("admin_") or data in ("back_admin", "close_menu"):
        await adm.handle_admin_callback(update, context)
        return

    await query.answer()

    if data == "noop":
        return

    elif data == "show_commands":
        text = (
            "\U0001f4cb **Sinzhu Waifu Bot Commands**\n\n"
            "\U0001f3af *User Commands:*\n"
            "/Clutch \u2014 Hunt a spawned waifu in groups\n"
            "/Store \u2014 Buy waifus from the store\n"
            "/Harem \u2014 View your waifu collection\n"
            "/Hclaim \u2014 Claim daily free waifu\n"
            "/TopChat \u2014 Top 10 Shinobi & Villages\n"
            "/Onex \u2014 Check your Onex balance\n"
            "/Redeem \u2014 Redeem a code for Onex\n"
            "/Wsell \u2014 Sell a waifu\n"
            "/Daily \u2014 Claim daily Onex\n"
            "/Weakly \u2014 Claim weekly gold\n"
            "/Tresure \u2014 Open treasure chest\n"
            "/Slavetime \u2014 Change waifu spawn time (admin)\n"
            "/Gift \u2014 Gift waifu to a friend\n"
            "/Ranks \u2014 See your rank card\n\n"
            "\U0001f451 *Admin Commands:*\n"
            "/Upload \u2014 Upload a waifu\n"
            "/Adsh \u2014 Add waifu to shop\n"
            "/Remove \u2014 Remove waifu from shop\n"
            "/Give \u2014 Give waifu to a user\n"
            "/Creddem \u2014 Create redeem code\n"
            "/Broadcast \u2014 Broadcast message\n"
            "/Setphoto \u2014 Set welcome photo\n"
            "/RemovePhoto \u2014 Remove welcome photo\n"
            "/Setcaption \u2014 Change welcome caption\n"
            "/ChangeButton \u2014 Change button links\n"
            "/GList \u2014 List all groups\n"
            "/Mlist \u2014 List all users"
        )
        kb = InlineKeyboardMarkup([[InlineKeyboardButton("\U0001f519 Back", callback_data="main_menu")]])
        await query.edit_message_text(text, reply_markup=kb, parse_mode="Markdown")

    elif data == "top_groups_btn":
        top_groups = db.get_top_groups(5)
        rows = []
        for g in top_groups:
            title = g["chat_title"] or str(g["chat_id"])
            chat_id_clean = str(g["chat_id"]).replace("-100", "")
            rows.append([InlineKeyboardButton(
                f"\U0001f3d8 {title} \u2014 {g['total_spawns']} spawns",
                url=f"https://t.me/c/{chat_id_clean}"
            )])
        rows.append([InlineKeyboardButton("\U0001f519 Back", callback_data="main_menu")])
        await query.edit_message_reply_markup(reply_markup=InlineKeyboardMarkup(rows))

    elif data == "main_menu":
        await query.edit_message_text(
            f"\U0001f338 **Welcome back, {user.first_name}!**\n\nChoose an option:",
            reply_markup=main_menu_keyboard(),
            parse_mode="Markdown"
        )

    elif data == "balance":
        u = db.get_user(user.id)
        kb = InlineKeyboardMarkup([
            [
                InlineKeyboardButton("\U0001f4e6 Daily", callback_data="daily"),
                InlineKeyboardButton("\U0001f6d2 Store", callback_data="shop_1"),
            ],
            [InlineKeyboardButton("\U0001f519 Back", callback_data="main_menu")],
        ])
        await query.edit_message_text(
            f"\U0001f4b0 **{user.first_name}'s Wallet**\n\n\U0001f48e Onex: `{u['onex']}`",
            reply_markup=kb,
            parse_mode="Markdown"
        )

    elif data == "daily":
        u = db.get_user(user.id)
        today = date.today().isoformat()
        if u["daily_claim"] == today:
            await query.edit_message_text(
                "\u23f0 Already claimed today!",
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("\U0001f519 Back", callback_data="main_menu")]])
            )
        else:
            reward = random.randint(200, 500)
            db.update_user(user.id, onex=u["onex"] + reward, daily_claim=today)
            await query.edit_message_text(
                f"\u2705 **Daily!**\n\n\U0001f4b0 +{reward} Onex\n\U0001f48e {u['onex'] + reward} Onex",
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("\U0001f519 Menu", callback_data="main_menu")]]),
                parse_mode="Markdown"
            )

    elif data == "welkin":
        u = db.get_user(user.id)
        today = date.today().isoformat()
        if u["welkin_claim"] == today:
            await query.edit_message_text(
                "\u23f0 Weekly already claimed!",
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("\U0001f519 Back", callback_data="main_menu")]])
            )
        else:
            db.update_user(user.id, onex=u["onex"] + 1000, welkin_claim=today)
            await query.edit_message_text(
                "\U0001f31f **Weekly Gold!** +1000 Onex",
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("\U0001f519 Menu", callback_data="main_menu")]]),
                parse_mode="Markdown"
            )

    elif data == "treasure":
        u = db.get_user(user.id)
        result = random.choices(["onex", "waifu", "nothing"], weights=[50, 30, 20], k=1)[0]
        if result == "onex":
            amount = random.randint(100, 1000)
            db.update_user(user.id, onex=u["onex"] + amount)
            text = f"\U0001f48e Treasure! Found **{amount} Onex**!"
        elif result == "waifu":
            waifus = db.get_all_waifus()
            if waifus:
                w = random.choice(waifus)
                db.give_waifu_to_user(user.id, w["id"])
                text = f"\U0001f48e Got **{w['name']}** ({w['rarity']})!"
            else:
                text = "\U0001f48e Empty chest! \U0001f622"
        else:
            text = "\U0001f48e Empty chest! \U0001f622"
        await query.edit_message_text(
            text,
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("\U0001f519 Menu", callback_data="main_menu")]]),
            parse_mode="Markdown"
        )

    elif data == "hclaim":
        u = db.get_user(user.id)
        today = date.today().isoformat()
        if u["hclaim_date"] == today:
            await query.edit_message_text(
                "\u23f0 Free waifu already claimed today!",
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("\U0001f519 Back", callback_data="main_menu")]])
            )
            return
        waifus = db.get_all_waifus()
        if not waifus:
            await query.edit_message_text("\u274c No waifus available!")
            return
        low_rarities = [w for w in waifus if w["rarity"] in list(RARITY_TIERS.keys())[:5]]
        w = random.choice(low_rarities if low_rarities else waifus)
        db.give_waifu_to_user(user.id, w["id"])
        db.update_user(user.id, hclaim_date=today)
        await query.edit_message_text(
            f"\U0001f381 **Free Waifu!**\n\n{w['name']} ({w['rarity']}) added!",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("\U0001f3b4 Harem", callback_data="harem_1"),
                 InlineKeyboardButton("\U0001f519 Menu", callback_data="main_menu")]
            ]),
            parse_mode="Markdown"
        )

    elif data == "redeem_start":
        await query.edit_message_text(
            "\U0001f3ab **Redeem Code**\n\nUse command: `/Redeem <code>`\n\nExample: `/Redeem SINZHU100`",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("\U0001f519 Back", callback_data="main_menu")]]),
            parse_mode="Markdown"
        )

    elif data == "top":
        top = db.get_top_collectors(10)
        text = "\U0001f3c6 **Top 10 Shinobi** (Collectors)\n\n"
        medals = ["\U0001f947", "\U0001f948", "\U0001f949"] + ["\U0001f539"] * 7
        for i, u in enumerate(top):
            name = f"@{u['username']}" if u["username"] else u["first_name"]
            text += f"{medals[i]} {name} \u2014 {u['total_waifus']} waifus\n"
        await query.edit_message_text(text, reply_markup=top_keyboard("collectors"), parse_mode="Markdown")

    elif data == "tops":
        top = db.get_top_rich(10)
        text = "\U0001f4b8 **Top 10 Richest**\n\n"
        medals = ["\U0001f947", "\U0001f948", "\U0001f949"] + ["\U0001f539"] * 7
        for i, u in enumerate(top):
            name = f"@{u['username']}" if u["username"] else u["first_name"]
            text += f"{medals[i]} {name} \u2014 {u['onex']} Onex\n"
        await query.edit_message_text(text, reply_markup=top_keyboard("rich"), parse_mode="Markdown")

    elif data == "rank":
        u = db.get_user(user.id)
        waifu_count = u["total_waifus"]
        current_rank, next_rank, next_min = get_rank(waifu_count)
        needed = (next_min - waifu_count) if next_min else 0
        text = (
            f"\U0001f340 **{user.first_name} Rank Card** \U0001f3f7\n"
            f"\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\n"
            f"\U0001f52e Rank: {current_rank}\n"
            f"\U0001f3b4 Waifus Collected: {waifu_count}\n"
        )
        if next_rank:
            text += f"\U0001f51c Next Rank: {next_rank} ({needed} more needed)\n"
        else:
            text += "\U0001f451 Highest rank achieved!\n"
        await query.edit_message_text(
            text,
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("\U0001f519 Menu", callback_data="main_menu")]]),
            parse_mode="Markdown"
        )

    elif data.startswith("harem_"):
        page = int(data.split("_")[1])
        waifus = db.get_user_waifus(user.id)
        if not waifus:
            await query.edit_message_text(
                "\U0001f494 Harem is empty!",
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("\U0001f519 Menu", callback_data="main_menu")]])
            )
            return
        chunk, total_pages = paginate(waifus, page, WAIFU_PER_PAGE)
        u_data = db.get_user(user.id)
        text = f"\U0001f3b4 **{user.first_name}'s Harem** ({len(waifus)} waifus)\n\n"
        for w in chunk:
            fav = " \u2b50" if u_data.get("favorite_waifu_id") == w["id"] else ""
            text += f"\u2022 {w['rarity']} **{w['name']}** \u2014 {w['anime']}{fav} [ID:{w['id']}]\n"
        await query.edit_message_text(
            text,
            reply_markup=harem_keyboard(chunk, page, total_pages, user.id),
            parse_mode="Markdown"
        )

    elif data.startswith("waifu_detail_"):
        uw_id = int(data.split("_")[2])
        waifu = db.get_waifu_by_uw_id(uw_id)
        u = db.get_user(user.id)
        if not waifu:
            await query.edit_message_text("\u274c Waifu not found!")
            return
        sell_price = RARITY_TIERS.get(waifu["rarity"], {}).get("sell_price", 50)
        text = (
            f"\U0001f3b4 **{waifu['name']}**\n\n"
            f"\U0001f4fa {waifu['anime']}\n"
            f"\u2b50 {waifu['rarity']}\n"
            f"\U0001f4b0 Sell: {sell_price} Onex\n"
            f"\U0001f194 ID: {uw_id}"
        )
        await query.edit_message_text(
            text,
            reply_markup=waifu_detail_keyboard(uw_id, u.get("favorite_waifu_id")),
            parse_mode="Markdown"
        )

    elif data.startswith("fav_"):
        uw_id = int(data.split("_")[1])
        waifu = db.get_waifu_by_uw_id(uw_id)
        u = db.get_user(user.id)
        if not waifu or waifu["user_id"] != user.id:
            await query.answer("\u274c Not your waifu!", show_alert=True)
            return
        new_fav = None if u.get("favorite_waifu_id") == uw_id else uw_id
        db.update_user(user.id, favorite_waifu_id=new_fav)
        await query.answer(f"\u2b50 {'Set as fav!' if new_fav else 'Removed from fav!'}", show_alert=True)
        await query.edit_message_reply_markup(
            reply_markup=waifu_detail_keyboard(uw_id, new_fav)
        )

    elif data.startswith("sell_confirm_"):
        uw_id = int(data.split("_")[2])
        waifu = db.get_waifu_by_uw_id(uw_id)
        if not waifu or waifu["user_id"] != user.id:
            await query.answer("\u274c Not your waifu!", show_alert=True)
            return
        sell_price = RARITY_TIERS.get(waifu["rarity"], {}).get("sell_price", 50)
        await query.edit_message_text(
            f"\U0001f4b8 Sell **{waifu['name']}** for {sell_price} Onex?",
            reply_markup=sell_confirm_keyboard(uw_id, sell_price),
            parse_mode="Markdown"
        )

    elif data.startswith("sell_do_"):
        uw_id = int(data.split("_")[2])
        waifu = db.get_waifu_by_uw_id(uw_id)
        if not waifu or waifu["user_id"] != user.id:
            await query.answer("\u274c Not your waifu!", show_alert=True)
            return
        sell_price = RARITY_TIERS.get(waifu["rarity"], {}).get("sell_price", 50)
        db.remove_user_waifu(uw_id, user.id)
        u = db.get_user(user.id)
        db.update_user(user.id, onex=u["onex"] + sell_price)
        await query.edit_message_text(
            f"\u2705 Sold **{waifu['name']}** for {sell_price} Onex!\n\U0001f48e Balance: {u['onex'] + sell_price}",
            reply_markup=InlineKeyboardMarkup([
                [
                    InlineKeyboardButton("\U0001f3b4 Harem", callback_data="harem_1"),
                    InlineKeyboardButton("\U0001f519 Menu", callback_data="main_menu"),
                ]
            ]),
            parse_mode="Markdown"
        )

    elif data.startswith("shop_"):
        page = int(data.split("_")[1])
        waifus = db.get_shop_waifus()
        if not waifus:
            await query.edit_message_text(
                "\U0001f6d2 Store is empty!",
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("\U0001f519 Menu", callback_data="main_menu")]])
            )
            return
        chunk, total_pages = paginate(waifus, page, WAIFU_PER_PAGE)
        await query.edit_message_text(
            f"\U0001f6d2 **Waifu Store** ({page}/{total_pages})",
            reply_markup=shop_keyboard(chunk, page, total_pages),
            parse_mode="Markdown"
        )

    elif data.startswith("buy_confirm_"):
        wid = int(data.split("_")[2])
        w = db.get_waifu_by_id(wid)
        if not w:
            await query.answer("\u274c Not found!", show_alert=True)
            return
        price = RARITY_TIERS.get(w["rarity"], {}).get("buy_price", 1000)
        await query.edit_message_text(
            f"\U0001f6d2 Buy **{w['name']}** for {price} Onex?",
            reply_markup=buy_confirm_keyboard(wid, price),
            parse_mode="Markdown"
        )

    elif data.startswith("buy_do_"):
        wid = int(data.split("_")[2])
        w = db.get_waifu_by_id(wid)
        if not w:
            await query.answer("\u274c Not found!", show_alert=True)
            return
        u = db.get_user(user.id)
        price = RARITY_TIERS.get(w["rarity"], {}).get("buy_price", 1000)
        if u["onex"] < price:
            await query.answer(f"\u274c Need {price} Onex!", show_alert=True)
            return
        db.update_user(user.id, onex=u["onex"] - price)
        db.give_waifu_to_user(user.id, wid)
        await query.edit_message_text(
            f"\u2705 Bought **{w['name']}!**\n\U0001f48e {u['onex'] - price} Onex left",
            reply_markup=InlineKeyboardMarkup([
                [
                    InlineKeyboardButton("\U0001f3b4 Harem", callback_data="harem_1"),
                    InlineKeyboardButton("\U0001f6d2 Store", callback_data="shop_1"),
                ]
            ]),
            parse_mode="Markdown"
        )

    elif data.startswith("quick_hunt_"):
        wid = int(data.split("_")[2])
        if update.effective_chat.type == "private":
            await query.answer("\u274c Groups only!", show_alert=True)
            return
        group = db.get_group(update.effective_chat.id)
        if group["current_waifu_claimed"]:
            await query.answer("\U0001f4a8 Already claimed!", show_alert=True)
            return
        if group["current_waifu_id"] != wid:
            await query.answer("\u274c No longer available!", show_alert=True)
            return
        db.update_group(update.effective_chat.id, current_waifu_claimed=1)
        db.get_user(user.id, user.username, user.first_name)
        db.give_waifu_to_user(user.id, wid)
        w = db.get_waifu_by_id(wid)
        wname = w["name"] if w else "Unknown"
        await query.edit_message_caption(
            caption=f"\u2705 **{get_display_name(user)} claimed {wname}!** \U0001f389\n\nUse /Harem to view collection.",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("\U0001f3b4 View Harem", callback_data="harem_1")]]),
            parse_mode="Markdown"
        )

# ─── MAIN ─────────────────────────────────────────────────

def main():
    db.init_db()

    app = Application.builder().token(BOT_TOKEN).build()

    # User commands
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("Clutch", clutch_cmd))
    app.add_handler(CommandHandler("clutch", clutch_cmd))
    app.add_handler(CommandHandler("Harem", harem_cmd))
    app.add_handler(CommandHandler("harem", harem_cmd))
    app.add_handler(CommandHandler("Hclaim", hclaim_cmd))
    app.add_handler(CommandHandler("hclaim", hclaim_cmd))
    app.add_handler(CommandHandler("Onex", onex_cmd))
    app.add_handler(CommandHandler("onex", onex_cmd))
    app.add_handler(CommandHandler("Daily", daily_cmd))
    app.add_handler(CommandHandler("daily", daily_cmd))
    app.add_handler(CommandHandler("Weakly", weekly_cmd))
    app.add_handler(CommandHandler("weakly", weekly_cmd))
    app.add_handler(CommandHandler("Tresure", treasure_cmd))
    app.add_handler(CommandHandler("tresure", treasure_cmd))
    app.add_handler(CommandHandler("Wsell", wsell_cmd))
    app.add_handler(CommandHandler("wsell", wsell_cmd))
    app.add_handler(CommandHandler("Gift", gift_cmd))
    app.add_handler(CommandHandler("gift", gift_cmd))
    app.add_handler(CommandHandler("Store", store_cmd))
    app.add_handler(CommandHandler("store", store_cmd))
    app.add_handler(CommandHandler("Ranks", ranks_cmd))
    app.add_handler(CommandHandler("ranks", ranks_cmd))
    app.add_handler(CommandHandler("TopChat", topchat_cmd))
    app.add_handler(CommandHandler("topchat", topchat_cmd))
    app.add_handler(CommandHandler("Redeem", redeem_cmd))
    app.add_handler(CommandHandler("redeem", redeem_cmd))
    app.add_handler(CommandHandler("Slavetime", slavetime_cmd))
    app.add_handler(CommandHandler("slavetime", slavetime_cmd))

    # Admin commands
    app.add_handler(CommandHandler("Upload", upload_cmd))
    app.add_handler(CommandHandler("upload", upload_cmd))
    app.add_handler(CommandHandler("Adsh", adsh_cmd))
    app.add_handler(CommandHandler("adsh", adsh_cmd))
    app.add_handler(CommandHandler("Remove", remove_cmd))
    app.add_handler(CommandHandler("Give", give_cmd))
    app.add_handler(CommandHandler("give", give_cmd))
    app.add_handler(CommandHandler("Creddem", creddem_cmd))
    app.add_handler(CommandHandler("creddem", creddem_cmd))
    app.add_handler(CommandHandler("Broadcast", broadcast_cmd))
    app.add_handler(CommandHandler("broadcast", broadcast_cmd))
    app.add_handler(CommandHandler("Setphoto", setphoto_cmd))
    app.add_handler(CommandHandler("RemovePhoto", removephoto_cmd))
    app.add_handler(CommandHandler("Setcaption", setcaption_cmd))
    app.add_handler(CommandHandler("ChangeButton", changebtn_cmd))
    app.add_handler(CommandHandler("GList", glist_cmd))
    app.add_handler(CommandHandler("glist", glist_cmd))
    app.add_handler(CommandHandler("Mlist", mlist_cmd))
    app.add_handler(CommandHandler("mlist", mlist_cmd))
    app.add_handler(CommandHandler("admin", adm.admin_panel))

    app.add_handler(CallbackQueryHandler(handle_callback))
    app.add_handler(MessageHandler(filters.ALL & ~filters.COMMAND, handle_message))

    print("Sinzhu Waifu Bot started!")
    app.run_polling(drop_pending_updates=True)


if __name__ == "__main__":
    main()
