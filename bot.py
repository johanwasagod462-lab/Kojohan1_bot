import asyncio
import time
from pyrogram import Client, filters
from pyrogram.types import ChatPermissions, ReplyKeyboardMarkup
from pyrogram.enums import ParseMode

# 🔑 CONFIG
API_ID = 38687584
API_HASH = "0d494cc2bb431a8bec250a3ebf224a59"
BOT_TOKEN = "8710028582:AAEnA5vtKyU4AsGz0tj8hebokm-VFOiZ-nc"
OWNER_ID = 7887055769

app = Client("advanced_single_bot", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN)

# 📦 STORAGE
group_data = {}
spam_tasks = {}
kills_data = {}
bot_admins = set()
cooldowns = {}

COMMANDS = [
    "All","Adm","Adms","Stop","Kick","Mute","Unmute",
    "Kill","Killl","Kills","Dlkills","Sp","Forgive",
    "Badm","Badms","Dlbadm","Send","Show"
]

# 🔧 HELPERS
def is_admin(user_id):
    return user_id == OWNER_ID or user_id in bot_admins

def get_group(chat_id):
    if chat_id not in group_data:
        group_data[chat_id] = {
            "sp": 1,
            "mention_running": False
        }
    return group_data[chat_id]

# 👥 MENTION
async def mention_all(client, message, admins_only=False, extra=""):
    chat_id = message.chat.id
    data = get_group(chat_id)

    if data["mention_running"]:
        return

    data["mention_running"] = True

    batch = []
    async for member in client.get_chat_members(chat_id):
        if not data["mention_running"]:
            break

        if admins_only and member.status not in ["administrator", "creator"]:
            continue

        user = member.user
        if user.is_bot:
            continue

        batch.append(f"[{user.first_name}](tg://user?id={user.id})")

        if len(batch) == 5:
            text = " ".join(batch) + f" {extra}"
            await message.reply_text(text, parse_mode=ParseMode.MARKDOWN)
            batch = []
            await asyncio.sleep(1)

    if batch:
        text = " ".join(batch) + f" {extra}"
        await message.reply_text(text, parse_mode=ParseMode.MARKDOWN)

    data["mention_running"] = False

# 🧠 MAIN
@app.on_message(filters.group & filters.text)
async def handler(client, message):
    text = message.text.strip()
    args = text.split()
    cmd = args[0].capitalize()

    if cmd not in COMMANDS:
        return

    user_id = message.from_user.id
    chat_id = message.chat.id

    if not is_admin(user_id):
        return

    try:
        await message.delete()
    except:
        pass

    data = get_group(chat_id)

    if cmd == "All":
        extra = " ".join(args[1:]) if len(args) > 1 else ""
        asyncio.create_task(mention_all(client, message, False, extra))

    elif cmd == "Adm":
        extra = " ".join(args[1:]) if len(args) > 1 else ""
        asyncio.create_task(mention_all(client, message, True, extra))

    elif cmd == "Adms":
        txt = "Admins:\n"
        async for m in client.get_chat_members(chat_id):
            if m.status in ["administrator", "creator"]:
                txt += f"[{m.user.first_name}](tg://user?id={m.user.id})\n"
        await message.reply_text(txt, parse_mode=ParseMode.MARKDOWN)

    elif cmd == "Stop":
        data["mention_running"] = False

    elif cmd == "Kick" and message.reply_to_message:
        await client.ban_chat_member(chat_id, message.reply_to_message.from_user.id)

    elif cmd == "Mute" and message.reply_to_message:
        await client.restrict_chat_member(chat_id, message.reply_to_message.from_user.id, ChatPermissions())

    elif cmd == "Unmute" and message.reply_to_message:
        await client.restrict_chat_member(
            chat_id,
            message.reply_to_message.from_user.id,
            ChatPermissions(can_send_messages=True)
        )

    elif cmd == "Kills":
        txt = " ".join(args[1:])
        kills_data.setdefault(chat_id, []).append(txt)

    elif cmd == "Killl":
        texts = kills_data.get(chat_id, [])
        out = "```\n" + "\n".join(texts) + "\n```"
        await message.reply_text(out)

    elif cmd == "Dlkills":
        txt = " ".join(args[1:])
        if chat_id in kills_data and txt in kills_data[chat_id]:
            kills_data[chat_id].remove(txt)

    elif cmd == "Sp":
        try:
            data["sp"] = float(args[1])
        except:
            pass

    elif cmd == "Kill" and message.reply_to_message:
        target = message.reply_to_message.from_user

        async def spam():
            while True:
                if chat_id not in spam_tasks:
                    break
                for t in kills_data.get(chat_id, []):
                    txt = f"[{target.first_name}](tg://user?id={target.id}) {t}"
                    await client.send_message(chat_id, txt, parse_mode=ParseMode.MARKDOWN)
                    await asyncio.sleep(data["sp"])

        spam_tasks[chat_id] = asyncio.create_task(spam())

    elif cmd == "Forgive":
        if chat_id in spam_tasks:
            spam_tasks[chat_id].cancel()
            del spam_tasks[chat_id]

    elif cmd == "Badm" and message.reply_to_message:
        bot_admins.add(message.reply_to_message.from_user.id)

    elif cmd == "Dlbadm" and message.reply_to_message:
        bot_admins.discard(message.reply_to_message.from_user.id)

    elif cmd == "Badms":
        txt = "Bot Admins:\n"
        for uid in bot_admins:
            txt += f"[User](tg://user?id={uid})\n"
        await message.reply_text(txt, parse_mode=ParseMode.MARKDOWN)

    elif cmd == "Send" and message.reply_to_message:
        for gid in group_data:
            try:
                await message.reply_to_message.copy(gid)
            except:
                pass

    elif cmd == "Show":
        keyboard = ReplyKeyboardMarkup(
            [
                ["All", "Adm", "Adms"],
                ["Kick", "Mute", "Unmute"],
                ["Kill", "Stop", "Forgive"],
                ["Badm", "Badms", "Send"],
                ["Hide"]
            ],
            resize_keyboard=True
        )
        await message.reply_text("Commands 👇", reply_markup=keyboard)

    elif cmd == "Hide":
        await message.reply_text("Keyboard hidden")

# 🎉 WELCOME (PFP FIXED)
@app.on_message(filters.new_chat_members)
async def welcome(client, message):
    for member in message.new_chat_members:
        user = await client.get_users(member.id)

        text = f"""📬ကြိုဆိုပါတယ်ဗျ။👋😉

📝Name📝 - {user.first_name}📝
💳Id💳 - {user.id}💳
📋Username📋 - @{user.username if user.username else 'None'}📋
"""

        if user.photo:
            await message.reply_photo(
                user.photo.big_file_id,
                caption=text
            )
        else:
            await message.reply_text(text)

# 👋 GOODBYE (PFP FIXED)
@app.on_message(filters.left_chat_member)
async def goodbye(client, message):
    user = await client.get_users(message.left_chat_member.id)

    text = f"""📬နှုတ်ဆက်ပါတယ်။👋😞

📝Name📝 - {user.first_name}📝
💳Id💳 - {user.id}💳
📋Username📋 - @{user.username if user.username else 'None'}📋
"""

    if user.photo:
        await message.reply_photo(
            user.photo.big_file_id,
            caption=text
        )
    else:
        await message.reply_text(text)

# 🚀 RUN
app.run()
