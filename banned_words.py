import json
import os

from .group_status import load_status, save_status

DATA_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data")
from app.api import send_group_msg, delete_msg, set_group_ban


async def is_group_owner(role):
    return role == "owner"


async def is_group_admin(role):
    return role == "admin"


async def is_authorized(user_id, role, owner_id):
    is_admin = await is_group_admin(role)
    is_owner = await is_group_owner(role)
    return (is_admin or is_owner) or (user_id in owner_id)


def load_banned_words(group_id):
    try:
        with open(
            f"{DATA_DIR}/banned_words_{group_id}.json", "r", encoding="utf-8"
        ) as f:
            return json.load(f)
    except FileNotFoundError:
        return []


def save_banned_words(group_id, banned_words):
    with open(f"{DATA_DIR}/banned_words_{group_id}.json", "w", encoding="utf-8") as f:
        json.dump(banned_words, f, ensure_ascii=False, indent=4)


def load_banned_words_status(group_id):
    return load_status(group_id, "banned_words_status")


def save_banned_words_status(group_id, status):
    save_status(group_id, "banned_words_status", status)


async def check_banned_words(websocket, group_id, msg):
    if not load_banned_words_status(group_id) or await is_authorized(
        msg["sender"]["user_id"], msg["sender"]["role"], msg["sender"]["user_id"]
    ):
        return False

    banned_words = load_banned_words(group_id)
    raw_message = msg["raw_message"]

    for word in banned_words:
        if word in raw_message:
            message_id = int(msg["message_id"])
            await delete_msg(websocket, message_id)
            warning_message = f"""警告：请不要发送违禁词！
如有误删是发的内容触发了违禁词，请及时联系管理员处理。

有新的事件被处理了，请查看是否正常处理[CQ:at,qq=2769731875]"""
            await send_group_msg(websocket, group_id, warning_message)
            user_id = msg["sender"]["user_id"]
            await set_group_ban(websocket, group_id, user_id, 60)
            return True

    return False


async def list_banned_words(websocket, group_id):
    banned_words = load_banned_words(group_id)
    if banned_words:
        banned_words_message = "违禁词列表:\n" + "\n".join(banned_words)
    else:
        banned_words_message = "违禁词列表为空。"
    await send_group_msg(websocket, group_id, banned_words_message)
