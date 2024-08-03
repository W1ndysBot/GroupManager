# 群管系统
import json
import logging
import re
import os
import random
import sys
from datetime import datetime

sys.path.append(
    os.path.dirname(
        os.path.dirname(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        )  # 获取了文件上级四层路径
    )
)
from app.api import *
from app.config import owner_id

# 定义数据目录
DATA_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data")


# 菜单提示
async def show_menu(websocket, group_id):
    menu_message = """
群管系统菜单:
违禁词管理:
- 添加违禁词: add_banned_word 违禁词 或 添加违禁词 违禁词
- 移除违禁词: remove_banned_word 违禁词 或 移除违禁词 违禁词
- 查看违禁词列表: list_banned_words 或 查看违禁词
- 开启违禁词检测: enable_banned_words 或 开启违禁词检测
- 关闭违禁词检测: disable_banned_words 或 关闭违禁词检测

禁言管理:
- 禁言自己随机时间: banme 或 禁言我
- 禁言指定用户: ban @用户 60 或 禁言 @用户 60
- 随机禁言一个用户: banrandom 或 随机禁言
- 解禁指定用户: unban @用户 或 解禁 @用户

群管理:
- 开启全员禁言: 全员禁言 或 mute_all
- 关闭全员禁言: 全员解禁 或 unmute_all
- 踢出指定用户: kick @用户 或 踢 @用户
- 撤回消息: recall 或 撤回

欢迎和欢送:
- 开启入群欢迎和退群欢送: enable_welcome_message 或 开启入群欢迎
- 关闭入群欢迎和退群欢送: disable_welcome_message 或 关闭入群欢迎

邀请链管理:
- 开启邀请链功能: enable_invite_chain 或 开启邀请链
- 关闭邀请链功能: disable_invite_chain 或 关闭邀请链
- 查看指定用户的邀请链: view_invite_chain 用户ID 或 查看邀请链 用户ID

视频检测管理:
- 开启视频检测: enable_video_check 或 开启视频检测
- 关闭视频检测: disable_video_check 或 关闭视频检测

群状态查看:
- 查看群内所有状态开关情况: view_group_status 或 查看群状态
    """
    await send_group_msg(websocket, group_id, menu_message)


# 判断用户是否是QQ群群主
async def is_qq_owner(role):
    if role == "owner":
        return True
    else:
        return False


# 判断用户是否是QQ群管理员
async def is_qq_admin(role):
    if role == "admin":
        return True
    else:
        return False


# 读取违禁词列表
def load_banned_words(group_id):
    try:
        with open(
            f"{DATA_DIR}/banned_words_{group_id}.json",
            "r",
            encoding="utf-8",
        ) as f:
            return json.load(f)
    except FileNotFoundError:
        return []


# 保存违禁词列表
def save_banned_words(group_id, banned_words):
    with open(
        f"{DATA_DIR}/banned_words_{group_id}.json",
        "w",
        encoding="utf-8",
    ) as f:
        json.dump(banned_words, f, ensure_ascii=False, indent=4)


# 读取状态
def load_status(group_id, key):
    try:
        with open(
            f"{DATA_DIR}/group_status.json",
            "r",
            encoding="utf-8",
        ) as f:
            data = json.load(f)
            # 遍历列表找到对应的 group_id
            for group_status in data:
                if group_status["group_id"] == group_id:
                    return group_status.get(key, False)  # 默认关闭
            return False  # 如果没有找到对应的 group_id，默认关闭
    except FileNotFoundError:
        return False  # 默认关闭


# 保存状态
def save_status(group_id, key, status):
    try:
        with open(
            f"{DATA_DIR}/group_status.json",
            "r",
            encoding="utf-8",
        ) as f:
            data = json.load(f)
    except FileNotFoundError:
        data = []

    # 查找是否已有该 group_id 的状态
    group_found = False
    for group_status in data:
        if group_status["group_id"] == group_id:
            group_status[key] = status
            group_found = True
            break

    # 如果没有找到该 group_id，则添加新的状态
    if not group_found:
        data.append({"group_id": group_id, key: status})

    with open(
        f"{DATA_DIR}/group_status.json",
        "w",
        encoding="utf-8",
    ) as f:
        json.dump(data, f, ensure_ascii=False, indent=4)


# 读取违禁词检测状态
def load_banned_words_status(group_id):
    return load_status(group_id, "banned_words_status")


# 保存违禁词检测状态
def save_banned_words_status(group_id, status):
    save_status(group_id, "banned_words_status", status)


# 读取视频检测状态
def load_video_check_status(group_id):
    return load_status(group_id, "video_check_status")


# 保存视频检测状态
def save_video_check_status(group_id, status):
    save_status(group_id, "video_check_status", status)


# 读取入群欢迎状态
def load_welcome_status(group_id):
    return load_status(group_id, "welcome_status")


# 保存入群欢迎状态
def save_welcome_status(group_id, status):
    save_status(group_id, "welcome_status", status)
    # 同步设置退群欢送状态
    save_farewell_status(group_id, status)


# 读取退群欢送状态
def load_farewell_status(group_id):
    return load_status(group_id, "farewell_status")


# 保存退群欢送状态
def save_farewell_status(group_id, status):
    save_status(group_id, "farewell_status", status)


# 读取邀请链状态
def load_invite_chain_status(group_id):
    return load_status(group_id, "invite_chain_status")


# 保存邀请链状态
def save_invite_chain_status(group_id, status):
    save_status(group_id, "invite_chain_status", status)


# 读取群状态
def load_group_status(group_id):
    try:
        with open(f"{DATA_DIR}/group_status.json", "r", encoding="utf-8") as f:
            group_status_list = json.load(f)
            for group_status in group_status_list:
                if group_status["group_id"] == group_id:
                    return group_status
            return None
    except FileNotFoundError:
        return None


# 查看违禁词列表
async def list_banned_words(websocket, group_id):
    banned_words = load_banned_words(group_id)
    if banned_words:
        banned_words_message = "违禁词列表:\n" + "\n".join(banned_words)
    else:
        banned_words_message = "违禁词列表为空。"
    await send_group_msg(websocket, group_id, banned_words_message)


# 禁言自己随机时间
async def banme_random_time(websocket, group_id, user_id):
    logging.info(f"执行禁言自己随机时间")
    # 随机时间
    ban_time = random.randint(1, 600)
    # 执行
    await set_group_ban(websocket, group_id, user_id, ban_time)
    logging.info(f"禁言{user_id} {ban_time} 秒。")


# 禁言指定用户
async def ban_user(websocket, group_id, message):
    # 初始化
    ban_qq = None
    ban_duration = None
    # 遍历message列表，查找type为'at'的项并读取qq字段
    for i, item in enumerate(message):
        if item["type"] == "at":
            ban_qq = item["data"]["qq"]
            # 检查下一个元素是否存在且类型为'text'
            if i + 1 < len(message) and message[i + 1]["type"] == "text":
                ban_duration = int(message[i + 1]["data"]["text"].strip())
            else:
                ban_duration = 60  # 默认60秒
    if ban_qq and ban_duration:
        # 执行
        await set_group_ban(websocket, group_id, ban_qq, ban_duration)


# 解禁
async def unban_user(websocket, group_id, message):
    logging.info("收到管理员的解禁消息。")
    # 初始化
    unban_qq = None
    # 遍历message列表，查找type为'at'的项并读取qq字段
    for item in message:
        if item["type"] == "at":
            unban_qq = item["data"]["qq"]
    # 执行
    await set_group_ban(websocket, group_id, unban_qq, 0)


# 随机禁言
async def ban_random_user(websocket, group_id, message):
    logging.info("收到管理员的随机禁言一个有缘人消息。")
    # 获取群成员列表
    response_data = await get_group_member_list(websocket, group_id, no_cache=True)
    logging.info(f"response_data: {response_data}")
    if response_data["status"] == "ok" and response_data["retcode"] == 0:
        members = response_data["data"]
        if members:
            # 过滤掉群主和管理员
            members = [
                member for member in members if member["role"] not in ["owner", "admin"]
            ]
            if members:
                # 随机选择一个成员
                random_member = random.choice(members)
                ban_qq = random_member["user_id"]
                ban_duration = random.randint(1, 600)  # 禁言该成员1分钟
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


# 检查违禁词
async def check_banned_words(websocket, group_id, msg):
    if not load_banned_words_status(group_id):
        return False  # 如果违禁词检测关闭，直接返回

    banned_words = load_banned_words(group_id)
    raw_message = msg["raw_message"]

    for word in banned_words:
        if word in raw_message:
            # 撤回消息
            message_id = int(msg["message_id"])
            await delete_msg(websocket, message_id)
            # 发送警告文案
            warning_message = f"""警告：请不要发送违禁词！
如有误删是发的内容触发了违禁词，请及时联系管理员处理。

有新的事件被处理了，请查看是否正常处理[CQ:at,qq=2769731875]"""
            await send_group_msg(websocket, group_id, warning_message)
            # 禁言1分钟
            user_id = msg["sender"]["user_id"]
            await set_group_ban(websocket, group_id, user_id, 60)
            return True

    # 检查是否包含视频
    if load_video_check_status(group_id) and any(
        item["type"] == "video" for item in msg["message"]
    ):
        # 撤回消息
        message_id = int(msg["message_id"])
        await delete_msg(websocket, message_id)
        await send_group_msg(websocket, group_id, "为防止广告，本群禁止发送视频")
        return True

    return False


# 扫描邀请链
async def view_invite_chain(websocket, group_id, target_user_id):
    if not load_invite_chain_status(group_id):
        await send_group_msg(websocket, group_id, "邀请链功能已关闭。")
        return

    invite_chain = load_invite_chain(group_id)
    if not invite_chain:
        await send_group_msg(websocket, group_id, "没有找到邀请链。")
        return

    def find_invite_chain(target_user_id, chain, visited):
        for inviter in invite_chain:
            if (
                inviter["user_id"] == target_user_id
                and inviter["user_id"] not in visited
            ):
                chain.append(inviter)
                visited.add(inviter["user_id"])
                find_invite_chain(inviter["operator_id"], chain, visited)

    chain = []
    visited = set()
    find_invite_chain(target_user_id, chain, visited)

    if chain:
        invite_chain_message = "邀请链:\n\n"
        for inviter in chain:
            invite_chain_message += f"【{inviter['operator_id']}】邀请了【{inviter['user_id']}】\n邀请时间：{inviter['date']}\n\n"
    else:
        invite_chain_message = "没有找到相关的邀请链。"

    await send_group_msg(websocket, group_id, invite_chain_message)


# 记录邀请链
async def save_invite_chain(group_id, user_id, operator_id):
    if not load_invite_chain_status(group_id):
        return

    # 加载整个群的邀请链
    invite_chain = load_invite_chain(group_id)

    # 更新特定用户的邀请链
    invite_chain.append(
        {
            "user_id": str(user_id),
            "operator_id": str(operator_id),
            "date": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        }
    )

    # 保存整个群的邀请链
    with open(
        f"{DATA_DIR}/invite_chain_{group_id}.json",
        "w",
        encoding="utf-8",
    ) as f:
        json.dump(invite_chain, f, ensure_ascii=False, indent=4)


# 删除邀请链
async def delete_invite_chain(group_id, user_id):
    invite_chain = load_invite_chain(group_id)
    if user_id in invite_chain:
        invite_chain.remove(user_id)
        with open(
            f"{DATA_DIR}/invite_chain_{group_id}.json",
            "w",
            encoding="utf-8",
        ) as f:
            json.dump(invite_chain, f, ensure_ascii=False, indent=4)


# 读取邀请链
def load_invite_chain(group_id):
    try:
        with open(
            f"{DATA_DIR}/invite_chain_{group_id}.json",
            "r",
            encoding="utf-8",
        ) as f:
            return json.load(f)
    except FileNotFoundError:
        return []


# 处理入群欢迎
async def handle_welcome_message(
    websocket,
    group_id,
    user_id,
):
    if load_welcome_status(group_id):
        welcome_message = f"欢迎[CQ:at,qq={user_id}]入群"
        if welcome_message:
            await send_group_msg(websocket, group_id, f"{welcome_message}")


# 处理退群欢送
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


# 处理群事件
async def handle_group_notice(websocket, msg):
    operator_id = msg["operator_id"]  # 入群操作者id
    sub_type = msg["sub_type"]  # 事件子类型
    user_id = msg["user_id"]
    group_id = msg["group_id"]

    # 入群消息
    if msg["notice_type"] == "group_increase":
        # 处理入群欢迎
        await handle_welcome_message(websocket, group_id, user_id)
        # 记录邀请链
        if (
            sub_type == "invite"
            or sub_type == "approve"
            and load_invite_chain_status(group_id)
        ):
            await save_invite_chain(group_id, user_id, operator_id)
            await send_group_msg(
                websocket,
                group_id,
                f"已记录 [CQ:at,qq={user_id}] 的邀请链，邀请者为 [CQ:at,qq={operator_id}] ，请勿在群内发送违规信息",
            )

    # 退群消息
    if msg["notice_type"] == "group_decrease":
        await handle_farewell_message(websocket, group_id, user_id, sub_type)


# 处理群消息
async def handle_group_message(websocket, msg):
    try:
        # 读取消息信息
        user_id = msg["user_id"]
        group_id = msg["group_id"]
        raw_message = msg["raw_message"]
        role = msg["sender"]["role"]
        message_id = int(msg["message_id"])

        # 鉴权
        is_admin = await is_qq_admin(role)
        is_owner = await is_qq_owner(role)
        is_authorized = (is_admin or is_owner) or (user_id in owner_id)

        # 显示菜单
        if raw_message == "群管系统" or raw_message == "group_manager" and is_authorized:
            await show_menu(websocket, group_id)

        # 检查是否为管理员发送的"测试"消息
        if is_authorized and (raw_message == "测试" or raw_message == "test"):
            logging.info("收到管理员的测试消息。")
            if raw_message == "测试":
                await send_group_msg(websocket, group_id, "测试成功")
            elif raw_message == "test":
                await send_group_msg(websocket, group_id, "Test successful")

        # 检查违禁词
        if await check_banned_words(websocket, group_id, msg):
            return

        # 全员禁言
        if raw_message == "全员禁言" or raw_message == "mute_all" and is_authorized:
            await set_group_whole_ban(websocket, group_id, True)  # 全员禁言

        # 全员解禁
        if raw_message == "全员解禁" or raw_message == "unmute_all" and is_authorized:
            await set_group_whole_ban(websocket, group_id, False)  # 全员解禁

        # 踢人
        if is_authorized and (
            re.match(r"kick.*", raw_message)
            or re.match(r"t.*", raw_message)
            or re.match(r"踢.*", raw_message)
        ):
            # 初始化
            kick_qq = None
            # 遍历message列表，查找type为'at'的项并读取qq字段
            for i, item in enumerate(msg["message"]):
                if item["type"] == "at":
                    kick_qq = item["data"]["qq"]
                    break
            # 执行
            if kick_qq:
                await set_group_kick(websocket, group_id, kick_qq)

        # 禁言命令
        if re.match(r"ban.*", raw_message):
            # 禁言自己随机时间
            if raw_message == "banme" or raw_message == "禁言我":
                await banme_random_time(websocket, group_id, user_id)
            # 禁言指定用户
            if (
                re.match(r"ban.*", raw_message) or re.match(r"禁言.*", raw_message)
            ) and is_authorized:
                await ban_user(websocket, group_id, msg["message"])
            # 随机禁言随机秒
            if (
                raw_message == "banrandom"
                or raw_message == "随机禁言"
                and is_authorized
            ):
                await ban_random_user(websocket, group_id, msg["message"])

        # 解禁
        if (
            re.match(r"unban.*", raw_message)
            or re.match(r"解禁.*", raw_message)
            and is_authorized
        ):
            await unban_user(websocket, group_id, msg["message"])

        # 撤回消息
        if "recall" in raw_message or "撤回" in raw_message and is_authorized:
            message_id = int(msg["message"][0]["data"]["id"])  # 获取回复消息的消息id
            await delete_msg(websocket, message_id)

        # 管理违禁词
        if is_authorized:
            if raw_message.startswith("add_banned_word ") or raw_message.startswith(
                "添加违禁词 "
            ):
                new_word = raw_message.split(" ", 1)[1].strip()
                banned_words = load_banned_words(group_id)
                if new_word not in banned_words:
                    banned_words.append(new_word)
                    save_banned_words(group_id, banned_words)
                    await send_group_msg(
                        websocket, group_id, f"已添加违禁词: {new_word}"
                    )
            elif raw_message.startswith(
                "remove_banned_word "
            ) or raw_message.startswith("移除违禁词 "):
                remove_word = raw_message.split(" ", 1)[1].strip()
                banned_words = load_banned_words(group_id)
                if remove_word in banned_words:
                    banned_words.remove(remove_word)
                    save_banned_words(group_id, banned_words)
                    await send_group_msg(
                        websocket, group_id, f"已移除违禁词: {remove_word}"
                    )
            elif raw_message == "list_banned_words" or raw_message == "查看违禁词":
                await list_banned_words(websocket, group_id)

        # 管理违禁词检测状态
        if is_authorized:
            if raw_message == "enable_banned_words" or raw_message == "开启违禁词检测":
                if load_banned_words_status(group_id):
                    await send_group_msg(
                        websocket, group_id, "违禁词检测已经开启了，无需重复开启。"
                    )
                else:
                    save_banned_words_status(group_id, True)
                    await send_group_msg(websocket, group_id, "已开启违禁词检测。")
            elif (
                raw_message == "disable_banned_words" or raw_message == "关闭违禁词检测"
            ):
                if not load_banned_words_status(group_id):
                    await send_group_msg(
                        websocket, group_id, "违禁词检测已经关闭了，无需重复关闭。"
                    )
                else:
                    save_banned_words_status(group_id, False)
                    await send_group_msg(websocket, group_id, "已关闭违禁词检测。")

        # 管理入群欢迎信息
        if is_authorized:
            if raw_message == "enable_welcome_message" or raw_message == "开启入群欢迎":
                if load_welcome_status(group_id):
                    await send_group_msg(
                        websocket,
                        group_id,
                        "入群欢迎和退群欢送已经开启了，无需重复开启。",
                    )
                else:
                    save_welcome_status(group_id, True)
                    await send_group_msg(
                        websocket, group_id, "已开启入群欢迎和退群欢送。"
                    )
            elif (
                raw_message == "disable_welcome_message"
                or raw_message == "关闭入群欢迎"
            ):
                if not load_welcome_status(group_id):
                    await send_group_msg(
                        websocket,
                        group_id,
                        "入群欢迎和退群欢送已经关闭了，无需重复关闭。",
                    )
                else:
                    save_welcome_status(group_id, False)
                    await send_group_msg(
                        websocket, group_id, "已关闭入群欢迎和退群欢送。"
                    )

        # 管理邀请链状态
        if is_authorized:
            if raw_message == "enable_invite_chain" or raw_message == "开启邀请链":
                if load_invite_chain_status(group_id):
                    await send_group_msg(
                        websocket, group_id, "邀请链功能已经开启过了，无需重复开启。"
                    )
                else:
                    save_invite_chain_status(group_id, True)
                    await send_group_msg(websocket, group_id, "已开启邀请链功能。")
            elif raw_message == "disable_invite_chain" or raw_message == "关闭邀请链":
                if not load_invite_chain_status(group_id):
                    await send_group_msg(
                        websocket, group_id, "邀请链功能已经关闭了，无需重复关闭。"
                    )
                else:
                    save_invite_chain_status(group_id, False)
                    await send_group_msg(websocket, group_id, "已关闭邀请链功能。")

        # 扫描邀请链
        if raw_message.startswith("view_invite_chain ") or raw_message.startswith(
            "查看邀请链 "
        ):
            target_user_id = raw_message.split(" ", 1)[1].strip()
            await view_invite_chain(websocket, group_id, target_user_id)

        # 管理视频检测状态
        if is_authorized:
            if raw_message == "enable_video_check" or raw_message == "开启视频检测":
                if load_video_check_status(group_id):
                    await send_group_msg(
                        websocket, group_id, "视频检测已经开启了，无需重复开启。"
                    )
                else:
                    save_video_check_status(group_id, True)
                    await send_group_msg(websocket, group_id, "已开启视频检测。")
            elif raw_message == "disable_video_check" or raw_message == "关闭视频检测":
                if not load_video_check_status(group_id):
                    await send_group_msg(
                        websocket, group_id, "视频检测已经关闭了，无需重复关闭。"
                    )
                else:
                    save_video_check_status(group_id, False)
                    await send_group_msg(websocket, group_id, "已关闭视频检测。")

        # 查看群内所有状态开关情况
        if raw_message == "view_group_status" or raw_message == "查看群状态":
            group_status = load_group_status(group_id)

            if group_status:
                status_message = (
                    f"群 {group_id} 的状态:\n"
                    f"邀请链功能: {group_status.get('invite_chain_status', False)}\n"
                    f"入群欢迎: {group_status.get('welcome_status', False)}\n"
                    f"退群欢送: {group_status.get('farewell_status', False)}\n"
                    f"违禁词检测: {group_status.get('banned_words_status', False)}\n"
                    f"视频检测: {group_status.get('video_check_status', False)}"
                )
            else:
                status_message = f"未找到群 {group_id} 的状态信息。"
            await send_group_msg(websocket, group_id, status_message)

    except Exception as e:
        logging.error(f"处理群消息时出错: {e}")
