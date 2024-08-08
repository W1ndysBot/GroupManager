from asyncio import create_task
import random
import logging
import sys
import os
import asyncio
import json
from datetime import datetime

from click import group

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from app.api import send_group_msg, set_group_ban, get_group_member_list


BAN_RECORDS = os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
    "data",
    "GroupManager",
)


async def banme_random_time(websocket, group_id, user_id):
    logging.info(f"执行禁言自己随机时间")
    ban_time = random.randint(1, 2592000)
    await set_group_ban(websocket, group_id, user_id, ban_time)
    logging.info(f"禁言{user_id} {ban_time} 秒。")


# 加载禁言记录
def load_ban_records(group_id):
    if os.path.exists(os.path.join(f"{BAN_RECORDS}", f"ban_records_{group_id}.json")):
        with open(
            os.path.join(f"{BAN_RECORDS}", f"ban_records_{group_id}.json"), "r"
        ) as f:
            try:
                return json.load(f)
            except json.JSONDecodeError:
                logging.error(
                    f"JSONDecodeError: 文件 ban_records_{group_id}.json 为空或格式错误。"
                )
                return {}
    return {}


# 保存禁言记录
def save_ban_records(records, group_id):
    with open(os.path.join(f"{BAN_RECORDS}", f"ban_records_{group_id}.json"), "w") as f:
        json.dump(records, f)


# 指定禁言一个人
async def ban_somebody(websocket, user_id, group_id, message):
    ban_qq = None
    ban_duration = None
    for i, item in enumerate(message):
        if item["type"] == "at":
            ban_qq = item["data"]["qq"]
            ban_duration = 60

    if ban_qq and ban_duration:
        records = load_ban_records(group_id)
        today = datetime.now().strftime("%Y-%m-%d")
        if ban_qq in records and records[ban_qq] == today:
            logging.info(f"用户 {ban_qq} 今天已经被禁言过了。")
            asyncio.create_task(
                send_group_msg(
                    websocket,
                    group_id,
                    f"[CQ:at,qq={user_id}] 你今天已经ban过别人一次了，还想ban？[CQ:face,id=14]。",
                )
            )
            return

        records[user_id] = today
        save_ban_records(records, group_id)
        asyncio.create_task(set_group_ban(websocket, group_id, ban_qq, ban_duration))


async def ban_user(websocket, group_id, message):
    ban_qq = None
    ban_duration = None
    for i, item in enumerate(message):
        if item["type"] == "at":
            ban_qq = item["data"]["qq"]
            if i + 1 < len(message) and message[i + 1]["type"] == "text":
                ban_duration = int(message[i + 1]["data"]["text"].strip())
            else:
                ban_duration = 60
    if ban_qq and ban_duration:
        await set_group_ban(websocket, group_id, ban_qq, ban_duration)


async def unban_user(websocket, group_id, message):
    logging.info("收到管理员的解禁消息。")
    unban_qq = None
    for item in message:
        if item["type"] == "at":
            unban_qq = item["data"]["qq"]
    await set_group_ban(websocket, group_id, unban_qq, 0)


async def ban_random_user(websocket, group_id, message):
    logging.info("收到管理员的随机禁言一个有缘人消息。")
    response_data = await get_group_member_list(websocket, group_id, no_cache=True)
    logging.info(f"response_data: {response_data}")
    if response_data["status"] == "ok" and response_data["retcode"] == 0:
        members = response_data["data"]
        if members:
            members = [
                member for member in members if member["role"] not in ["owner", "admin"]
            ]
            if members:
                random_member = random.choice(members)
                ban_qq = random_member["user_id"]
                ban_duration = random.randint(1, 600)
                ban_message = f"让我们恭喜 [CQ:at,qq={ban_qq}] 被禁言了 {ban_duration} 秒。\n注：群主及管理员无法被禁言。"
                await set_group_ban(websocket, group_id, ban_qq, ban_duration)
            else:
                logging.info("没有可禁言的成员。")
                ban_message = "没有可禁言的成员。"
        else:
            logging.info("群成员列表为空。")
            ban_message = "群成员列表为空。"

        await send_group_msg(websocket, group_id, ban_message)
    else:
        logging.error(f"处理消息时出错: {response_data}")
