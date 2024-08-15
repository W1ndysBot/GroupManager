import logging
import re
import os
import sys
import asyncio

sys.path.append(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
)


from app.scripts.GroupManager.group_management import *


from app.api import *
from app.config import owner_id
from app.switch import load_switch, save_switch

DATA_DIR = os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
    "data",
    "GroupManager",
)


# 是否是群主
def is_group_owner(role):
    return role == "owner"


# 是否是管理员
def is_group_admin(role):
    return role == "admin"


# 是否是管理员或群主或root管理员
def is_authorized(role, user_id):
    is_admin = is_group_admin(role)
    is_owner = is_group_owner(role)
    return (is_admin or is_owner) or (user_id in owner_id)


async def handle_GroupManager_group_message(websocket, msg):
    try:
        user_id = msg["user_id"]
        group_id = msg["group_id"]
        raw_message = msg["raw_message"]
        role = msg["sender"]["role"]
        message_id = int(msg["message_id"])
        self_id = str(msg.get("self_id", ""))  # 机器人QQ，转为字符串方便操作

        is_admin = is_group_admin(role)  # 是否是群管理员
        is_owner = is_group_owner(role)  # 是否是群主
        is_authorized = (is_admin or is_owner) or (
            user_id in owner_id
        )  # 是否是群主或管理员或root管理员

        if is_authorized and (raw_message == "测试" or raw_message == "test"):
            logging.info("收到管理员的测试消息。")
            if raw_message == "测试":
                await send_group_msg(websocket, group_id, "测试成功")
            elif raw_message == "test":
                await send_group_msg(websocket, group_id, "Test successful")

        if raw_message == "banall" and is_authorized:
            await set_group_whole_ban(websocket, group_id, True)
            return
        if raw_message == "unbanall" and is_authorized:
            await set_group_whole_ban(websocket, group_id, False)
            return

        if is_authorized and re.match(r"t.*", raw_message):
            kick_qq = None
            kick_qq = next(
                (item["data"]["qq"] for item in msg["message"] if item["type"] == "at"),
                None,
            )

            if kick_qq == self_id:
                await send_group_msg(websocket, group_id, "踢我干什么！")
                return

            if kick_qq:
                await set_group_kick(websocket, group_id, kick_qq)
                await send_group_msg(
                    websocket, group_id, f"[CQ:reply,id={message_id}] 已踢出 {kick_qq}"
                )
        if re.match(r"ban.*", raw_message):

            # 指定禁言一个人
            if re.match(r"banyou.*", raw_message):

                await ban_somebody(
                    websocket, user_id, group_id, msg["message"], self_id
                )
                return

            # 禁言自己
            if raw_message == "banme" or raw_message == "禁言我":
                await banme_random_time(websocket, group_id, user_id)
                return

            # 随机禁言
            if (
                raw_message == "banrandom" or raw_message == "随机禁言"
            ) and is_authorized:
                await ban_random_user(websocket, group_id, msg["message"])
                return

            # 禁言指定用户
            if (
                re.match(r"ban.*", raw_message) or re.match(r"禁言.*", raw_message)
            ) and is_authorized:

                await ban_user(websocket, group_id, msg["message"], self_id, user_id)

        # 解禁
        if (
            re.match(r"unban.*", raw_message) or re.match(r"解禁.*", raw_message)
        ) and is_authorized:
            await unban_user(websocket, group_id, msg["message"])

        # 撤回消息
        if "recall" in raw_message or "撤回" in raw_message and is_authorized:
            message_id = int(msg["message"][0]["data"]["id"])
            await delete_msg(websocket, message_id)

    except Exception as e:
        logging.error(f"处理群消息时出错: {e}")
