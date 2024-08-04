from .group_status import load_status, save_status
import sys
import os

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from app.api import send_group_msg


def load_welcome_status(group_id):
    return load_status(group_id, "welcome_status")


def save_welcome_status(group_id, status):
    save_status(group_id, "welcome_status", status)
    save_farewell_status(group_id, status)


def load_farewell_status(group_id):
    return load_status(group_id, "farewell_status")


def save_farewell_status(group_id, status):
    save_status(group_id, "farewell_status", status)


async def handle_welcome_message(websocket, group_id, user_id):
    if load_welcome_status(group_id):
        welcome_message = f"欢迎[CQ:at,qq={user_id}]入群"
        if welcome_message:
            await send_group_msg(websocket, group_id, f"{welcome_message}")


async def handle_farewell_message(websocket, group_id, user_id, sub_type):
    if load_farewell_status(group_id):
        if sub_type == "kick":
            farewell_message = f"{user_id} 已被踢出群聊🎉"
            if farewell_message:
                await send_group_msg(websocket, group_id, f"{farewell_message}")
        elif sub_type == "leave":
            farewell_message = f"{user_id} 退群了😭"
            if farewell_message:
                await send_group_msg(websocket, group_id, f"{farewell_message}")
