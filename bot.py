import asyncio
import logging
import re
import sqlite3
import os
from datetime import datetime, timezone
from pathlib import Path
from threading import Thread
from flask import Flask, request

from aiogram import Bot, Dispatcher, F
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.filters import Command, CommandStart
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton, ReplyKeyboardMarkup, KeyboardButton, Update

# ===== SETTINGS =====
BOT_TOKEN = "8742007360:AAHjHkYlUa3R0ICa2LWHYvmYsMUa0KWlac8"
OWNER_ID = 7375899145

# ဒီနေရာမှာ သင့် Render က ပေးထားတဲ့ URL ကို ထည့်ပါ (ဥပမာ: "https://my-1max-bot.onrender.com")
# Deploy လုပ်ပြီး URL ရမှ ဒီနေရာမှာ ပြန်ပြင်ပါ။ ခဏတာ ဒီအတိုင်းထားပါ။
RENDER_URL = "https://your-app-name.onrender.com" 

logging.basicConfig(level=logging.INFO)
log = logging.getLogger("bot")

DB_PATH = Path(__file__).resolve().parent / "boost_bot.sqlite3"
bot = Bot(BOT_TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
dp = Dispatcher()

# Flask Web Server (Render အတွက်)
app = Flask(__name__)

@app.route("/")
def index():
    return "Bot is running!"

@app.route(f"/webhook/{BOT_TOKEN}", methods=["POST"])
async def webhook():
    update = Update.model_validate(await request.get_json(force=True))
    await dp.feed_update(bot, update)
    return "ok"

def run_flask():
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 8080)))

# State variables
pending_registration = {}
order_drafts = {}
waiting_for = {}
support_waiting = set()

service_labels = {"likes": "Likes", "views": "Views", "followers": "Followers", "shares": "Shares", "saves": "Saves"}
FREE_COSTS = {"likes": 100, "views": 200, "followers": 30, "shares": 50, "saves": 50}

def db():
    con = sqlite3.connect(DB_PATH, timeout=20)
    con.row_factory = sqlite3.Row
    return con

def init_db():
    with db() as con:
        con.executescript("""
        CREATE TABLE IF NOT EXISTS users (user_id INTEGER PRIMARY KEY, username TEXT, balance INTEGER DEFAULT 0);
        CREATE TABLE IF NOT EXISTS orders (id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER, code TEXT UNIQUE, kind TEXT, service TEXT, link TEXT, qty INTEGER, cost INTEGER, status TEXT, created_at TEXT);
        """)

def now(): return datetime.now(timezone.utc).isoformat()

def get_user(uid):
    with db() as con: return con.execute("SELECT * FROM users WHERE user_id=?", (uid,)).fetchone()

def main_kb():
    return ReplyKeyboardMarkup(keyboard=[
        [KeyboardButton(text="🚀 Boost"), KeyboardButton(text="🪙 Balance")],
        [KeyboardButton(text="🎁 Bonus"), KeyboardButton(text="🎯 Tasks")],
    ], resize_keyboard=True)

def services_kb():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="TikTok Likes", callback_data="srv:likes")],
        [InlineKeyboardButton(text="TikTok Views", callback_data="srv:views")],
    ])

def confirm_kb(oid):
    return InlineKeyboardMarkup(inline_keyboard=[[
        InlineKeyboardButton(text="✅ Confirm", callback_data=f"confirm:{oid}"),
        InlineKeyboardButton(text="❌ Cancel", callback_data=f"cancel:{oid}")
    ]])

def owner_kb(oid):
    return InlineKeyboardMarkup(inline_keyboard=[[
        InlineKeyboardButton(text="✅ Approve", callback_data=f"approve:{oid}"),
        InlineKeyboardButton(text="❌ Reject", callback_data=f"reject:{oid}")
    ]])

@dp.message(CommandStart())
async def cmd_start(message: Message):
    uid = message.from_user.id
    with db() as con:
        if not con.execute("SELECT 1 FROM users WHERE user_id=?", (uid,)).fetchone():
            con.execute("INSERT INTO users (user_id, username, balance) VALUES (?, ?, 100)", (uid, message.from_user.username))
            await message.answer("Registration Success! +100 Bonus Coins.", reply_markup=main_kb())
        else:
            await message.answer("Welcome back!", reply_markup=main_kb())

@dp.message(F.text)
async def handle_text(message: Message):
    uid = message.from_user.id
    text = message.text.strip()

    if text == "🪙 Balance":
        u = get_user(uid)
        await message.answer(f"Balance: {u['balance']} Coins")
    elif text == "🎁 Bonus":
        with db() as con:
            con.execute("UPDATE users SET balance = balance + 100 WHERE user_id=?", (uid,))
        await message.answer("Claimed +100 Coins!")
    elif text == "🚀 Boost":
        await message.answer("Select service:", reply_markup=services_kb())
    elif text == "🎯 Tasks":
        await message.answer("No tasks available currently.")
    else:
        state = waiting_for.get(uid)
        if state == "link":
            order_drafts[uid]["link"] = text
            waiting_for[uid] = "qty"
            await message.answer("Enter quantity:")
        elif state == "qty":
            if not text.isdigit(): return
            qty = int(text)
            draft = order_drafts[uid]
            cost = (qty // 100) * FREE_COSTS[draft["service"]]
            if get_user(uid)["balance"] < cost:
                await message.answer("Not enough Coins.")
                waiting_for.pop(uid, None); order_drafts.pop(uid, None); return
            with db() as con:
                code = f"ORD-{int(datetime.now().timestamp())}"
                cur = con.execute("INSERT INTO orders (user_id, code, kind, service, link, qty, cost, status, created_at) VALUES (?, ?, 'free', ?, ?, ?, ?, 'DRAFT', ?)", (uid, code, draft["service"], draft["link"], qty, cost, now()))
                oid = cur.lastrowid
            waiting_for.pop(uid, None); order_drafts.pop(uid, None)
            await message.answer(f"Order: {code}\nCost: {cost} Coins\nConfirm?", reply_markup=confirm_kb(oid))

@dp.callback_query(F.data.startswith("srv:"))
async def cb_service(call: CallbackQuery):
    uid = call.from_user.id
    order_drafts[uid] = {"service": call.data.split(":")[1]}
    waiting_for[uid] = "link"
    await call.message.answer("Send TikTok link:")
    await call.answer()

@dp.callback_query(F.data.startswith("confirm:"))
async def cb_confirm(call: CallbackQuery):
    oid = int(call.data.split(":")[1])
    with db() as con:
        con.execute("UPDATE orders SET status='PENDING' WHERE id=?", (oid,))
        order = con.execute("SELECT * FROM orders WHERE id=?", (oid,)).fetchone()
    await call.message.answer("Order submitted to Owner.")
    try:
        await bot.send_message(OWNER_ID, f"New Order: {order['code']}\nUser: {call.from_user.id}\nCost: {order['cost']}", reply_markup=owner_kb(oid))
    except: pass
    await call.answer()

@dp.callback_query(F.data.startswith("approve:"))
async def cb_approve(call: CallbackQuery):
    if call.from_user.id != OWNER_ID: return await call.answer("Owner only.", show_alert=True)
    oid = int(call.data.split(":")[1])
    with db() as con:
        order = con.execute("SELECT * FROM orders WHERE id=?", (oid,)).fetchone()
        if order and order["status"] == "PENDING":
            con.execute("UPDATE users SET balance = balance - ? WHERE user_id=?", (order["cost"], order["user_id"]))
            con.execute("UPDATE orders SET status='APPROVED' WHERE id=?", (oid,))
            await bot.send_message(order["user_id"], f"✅ Order {order['code']} Approved!")
    await call.message.edit_reply_markup(reply_markup=None)
    await call.answer("Approved")

async def on_startup():
    init_db()
    webhook_url = f"{RENDER_URL}/webhook/{BOT_TOKEN}"
    await bot.set_webhook(webhook_url)
    log.info(f"Webhook set to {webhook_url}")

if __name__ == "__main__":
    # Flask ကို Background မှာ run မယ် (Render အတွက် လိုအပ်တယ်)
    Thread(target=run_flask).start()
    # Bot ကို Webhook Mode နဲ့ run မယ်
    asyncio.run(on_startup())
