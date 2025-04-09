import random
import logging
import sys
import os
import json
from datetime import datetime, date
import math
import re


sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from app.api import send_group_msg, set_group_ban, get_group_member_list


BAN_RECORDS = os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
    "data",
    "GroupManager",
)

from app.config import owner_id


async def banme_random_time(websocket, group_id, user_id, message_id):
    try:
        logging.info(f"执行禁言自己随机时间")

        # 保持抽中的禁言时间在1秒到30天之间
        ban_time = random.randint(1, 2592000)  # 1秒到30天

        # 使用对数函数计算实际禁言时间，最短1秒，最长5分钟
        actual_ban_time = min(int(math.log(ban_time, 1.07)) + 1, 300)
        await set_group_ban(websocket, group_id, user_id, actual_ban_time)

        # 加载当前用户的今日最高禁言时间
        user_max_ban_records = load_user_max_ban_records(group_id, user_id)

        # 加载当前群的今日最高禁言时间
        max_ban_records, max_ban_user = load_group_max_ban_user_records(group_id)

        # 检查是否打破本群的今日最高禁言记录
        if ban_time > max_ban_records:
            # 更新群的今日最高禁言记录
            save_user_max_ban_records(group_id, user_id, ban_time)

            await send_group_msg(
                websocket,
                group_id,
                f"[CQ:reply,id={message_id}]恭喜你打破本群今日的最高禁言记录！你抽中了 {ban_time} 秒的禁言时间，"
                f"根据宇宙卷卷对数函数弹性计算公式实际被禁言了 {actual_ban_time} 秒。现在本群今日的最高记录是 {ban_time} 秒，保持者是{user_id}。",
            )
        else:
            max_ban_user_str = f"，保持者是{max_ban_user}" if max_ban_user else ""

            if ban_time > user_max_ban_records:
                # 更新当前用户今日最高禁言记录
                save_user_max_ban_records(group_id, user_id, ban_time)

            await send_group_msg(
                websocket,
                group_id,
                f"[CQ:reply,id={message_id}]你抽中了 {ban_time} 秒的禁言时间，根据宇宙卷卷对数函数弹性计算公式实际被禁言了 {actual_ban_time} 秒。"
                f"今日群的最高禁言记录是 {max_ban_records} 秒{max_ban_user_str}。",
            )
    except Exception as e:
        logging.error(f"执行禁言自己随机时间时出错: {e}")
        await send_group_msg(
            websocket,
            group_id,
            f"执行禁言操作时发生错误，请稍后再试或联系管理员。",
        )


# 加载群的今日最高禁言记录，返回禁言时间最长的用户ID和时间
def load_group_max_ban_user_records(group_id):
    file_path = os.path.join(BAN_RECORDS, f"max_ban_records_{group_id}.json")
    # 如果文件不存在，则创建文件
    if not os.path.exists(file_path):
        # 创建目录
        os.makedirs(os.path.dirname(file_path), exist_ok=True)
        # 创建文件
        with open(file_path, "w") as wf:
            json.dump({date.today().isoformat(): {}}, wf, indent=4)
    today = date.today().isoformat()
    try:
        if os.path.exists(file_path):
            with open(file_path, "r") as f:
                records = json.load(f)
                if today in records and records[today]:
                    max_user = max(records[today], key=records[today].get)
                    return records[today][max_user], max_user
        else:
            with open(file_path, "w") as wf:
                json.dump({today: {}}, wf, indent=4)
        return 0, None
    except json.JSONDecodeError:
        logging.error(f"JSONDecodeError: 文件 {file_path} 为空或格式错误。")
        with open(file_path, "w") as wf:
            json.dump({today: {}}, wf, indent=4)
        return 0, None


def load_user_max_ban_records(group_id, user_id):
    file_path = os.path.join(BAN_RECORDS, f"max_ban_records_{group_id}.json")

    # 如果文件不存在，则创建文件
    if not os.path.exists(file_path):
        # 创建目录
        os.makedirs(os.path.dirname(file_path), exist_ok=True)
        # 创建文件
        with open(file_path, "w") as wf:
            json.dump({date.today().isoformat(): {}}, wf, indent=4)

    today = date.today().isoformat()
    try:
        if os.path.exists(file_path):
            with open(file_path, "r") as f:
                records = json.load(f)
                if today in records:
                    return records[today].get(str(user_id), 0)
        else:
            with open(file_path, "w") as wf:
                json.dump({today: {}}, wf, indent=4)
        return 0
    except json.JSONDecodeError:
        logging.error(f"JSONDecodeError: 文件 {file_path} 为空或格式错误。")
        return 0


def save_user_max_ban_records(group_id, user_id, ban_time):
    file_path = os.path.join(BAN_RECORDS, f"max_ban_records_{group_id}.json")
    today = date.today().isoformat()
    if os.path.exists(file_path):
        with open(file_path, "r") as f:
            records = json.load(f)
    else:
        # 创建目录
        os.makedirs(os.path.dirname(file_path), exist_ok=True)
        # 创建文件
        with open(file_path, "w") as wf:
            json.dump({today: {}}, wf, indent=4)
        records = {}

    if today not in records:
        records[today] = {}

    # 更新指定 user_id 的今日最高禁言记录
    records[today][str(user_id)] = ban_time

    with open(file_path, "w") as f:
        json.dump(records, f, indent=4)


# 加载banyou禁言记录
def load_ban_records(group_id):
    file_path = os.path.join(BAN_RECORDS, f"ban_records_{group_id}.json")
    if os.path.exists(file_path):
        with open(file_path, "r") as f:
            try:
                return json.load(f)
            except json.JSONDecodeError:
                logging.error(
                    f"JSONDecodeError: 文件 ban_records_{group_id}.json 为空或格式错误。"
                )
                # 如果文件不存在，创建一个空文件并初始化为空字典
                with open(file_path, "w") as wf:
                    json.dump({}, wf, indent=4)
                return {}
    return {}


# 保存banyou禁言记录
def save_ban_records(user_id, group_id):
    records = load_ban_records(group_id)

    # 更新或添加指定 user_id 的禁言记录
    records[str(user_id)] = datetime.now().strftime("%Y-%m-%d")

    with open(os.path.join(BAN_RECORDS, f"ban_records_{group_id}.json"), "w") as f:
        json.dump(records, f, indent=4)  # 使用 indent 参数进行格式化


# 指定禁言一个人
async def ban_somebody(websocket, user_id, group_id, message, self_id):
    if group_id == "798794707":
        return
    ban_qq = None
    ban_duration = None
    ban_qq = next(
        (item["data"]["qq"] for item in message if item["type"] == "at"), None
    )
    ban_duration = 60 if ban_qq else None

    if ban_qq and ban_duration:

        if ban_qq == self_id:
            await send_group_msg(websocket, group_id, "禁我干什么！")
            return

        if ban_qq == "2902284437":
            await send_group_msg(websocket, group_id, "禁海鲜干什么，给你来一分钟！")
            ban_duration = 60
            await set_group_ban(websocket, group_id, user_id, ban_duration)
            return

        if ban_qq == "2769731875":
            await send_group_msg(websocket, group_id, "禁W1ndys干什么，ban你！")
            ban_duration = int(random.paretovariate(1.5) * 60)
            ban_duration = min(ban_duration, 2592000)
            await set_group_ban(websocket, group_id, user_id, ban_duration)
            return

        records = load_ban_records(group_id)
        today = datetime.now().strftime("%Y-%m-%d")
        if str(user_id) in records and records[str(user_id)] == today:
            await send_group_msg(
                websocket,
                group_id,
                f"[CQ:at,qq={user_id}] 你今天已经ban过别人一次了，还想ban？[CQ:face,id=14]。",
            )
            return

        save_ban_records(user_id, group_id)
        await set_group_ban(websocket, group_id, ban_qq, ban_duration)


# 修改ban_user函数支持批量禁言
async def ban_user(websocket, group_id, message, self_id, user_id, message_id):
    try:
        # 获取所有被@的用户QQ号
        at_users = [item["data"]["qq"] for item in message if item["type"] == "at"]

        if not at_users:
            await send_group_msg(
                websocket, group_id, f"[CQ:reply,id={message_id}]请@要禁言的用户"
            )
            return

        # 检查是否尝试禁言机器人自己
        if self_id in at_users:
            await send_group_msg(
                websocket, group_id, f"[CQ:reply,id={message_id}]不能禁言我自己！"
            )
            at_users.remove(self_id)  # 从列表中移除机器人自己
            if not at_users:  # 如果没有其他人了，就直接返回
                return

        # 尝试提取禁言时间
        raw_message = " ".join(
            [item["data"]["text"] for item in message if item["type"] == "text"]
        )
        ban_time = 60  # 默认60秒

        # 查找数字
        duration_match = re.search(r"\d+", raw_message)
        if duration_match:
            ban_time = int(duration_match.group())

        # 批量禁言
        banned_users = []
        for ban_qq in at_users:
            await set_group_ban(websocket, group_id, ban_qq, ban_time)
            banned_users.append(ban_qq)

        if banned_users:
            await send_group_msg(
                websocket,
                group_id,
                f"[CQ:reply,id={message_id}]已禁言用户: {', '.join(banned_users)} {ban_time}秒",
            )
    except Exception as e:
        logging.error(f"禁言用户出错: {e}")


# 修改unban_user函数支持批量解禁
async def unban_user(websocket, group_id, message, message_id):
    try:
        # 获取所有被@的用户QQ号
        at_users = [item["data"]["qq"] for item in message if item["type"] == "at"]

        if not at_users:
            await send_group_msg(
                websocket, group_id, f"[CQ:reply,id={message_id}]请@要解除禁言的用户"
            )
            return

        # 批量解禁
        unbanned_users = []
        for unban_qq in at_users:
            await set_group_ban(websocket, group_id, unban_qq, 0)  # 0秒表示解除禁言
            unbanned_users.append(unban_qq)

        if unbanned_users:
            await send_group_msg(
                websocket,
                group_id,
                f"[CQ:reply,id={message_id}]已解除禁言: {', '.join(unbanned_users)}",
            )
    except Exception as e:
        logging.error(f"解除禁言出错: {e}")


async def ban_random_user(websocket, group_id, message):
    logging.info("收到管理员的随机禁言一个有缘人消息。")
    response_data = await get_group_member_list(websocket, group_id, no_cache=True)
    # logging.info(f"response_data: {response_data}")
    members = response_data
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


# 获取某群的banme最高记录
def get_ban_records(group_id, today):
    file_path = os.path.join(BAN_RECORDS, f"max_ban_records_{group_id}.json")
    if os.path.exists(file_path):
        with open(file_path, "r") as f:
            try:
                records = json.load(f)
                if today in records:
                    today_records = records[today]
                    sorted_records = sorted(
                        today_records.items(), key=lambda x: x[1], reverse=True
                    )
                    return sorted_records
                else:
                    logging.warning(f"没有找到日期 {today} 的记录。")
                    return []
            except json.JSONDecodeError:
                logging.error(
                    f"JSONDecodeError: 文件 max_ban_records_{group_id}.json 为空或格式错误。"
                )
                return []
    return []


# 查看禁言排行
async def banme_rank(websocket, group_id, message_id):
    today = datetime.now().strftime("%Y-%m-%d")
    ban_records = get_ban_records(group_id, today)
    if ban_records:
        logging.info(f"获取{group_id}今日禁言排行")
        message = f"[CQ:reply,id={message_id}]今日禁言排行：\n"
        for idx, record in enumerate(ban_records[:10], 1):
            message += f"{idx}. <{record[0]}>：{record[1]} 秒\n"
        await send_group_msg(
            websocket,
            group_id,
            message,
        )
    else:
        await send_group_msg(
            websocket,
            group_id,
            f"[CQ:reply,id={message_id}]今日没有禁言记录。",
        )
