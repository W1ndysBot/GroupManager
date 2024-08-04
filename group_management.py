import random
import logging
import sys
import os

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from app.api import send_group_msg, set_group_ban, get_group_member_list


async def banme_random_time(websocket, group_id, user_id):
    logging.info(f"执行禁言自己随机时间")
    ban_time = random.randint(1, 600)
    await set_group_ban(websocket, group_id, user_id, ban_time)
    logging.info(f"禁言{user_id} {ban_time} 秒。")


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
