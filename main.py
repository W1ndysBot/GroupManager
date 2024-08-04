import json
import logging
import re
import os
import sys
from .banned_words import *
from .group_status import *
from .invite_chain import *
from .welcome_farewell import *
from .group_management import *

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from app.api import *
from app.config import owner_id

sys.path.append(
    os.path.dirname(
        os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    )
)

DATA_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data")


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


async def is_group_owner(role):
    return role == "owner"


async def is_group_admin(role):
    return role == "admin"


async def handle_group_notice(websocket, msg):
    operator_id = msg["operator_id"]
    sub_type = msg["sub_type"]
    user_id = msg["user_id"]
    group_id = msg["group_id"]

    if msg["notice_type"] == "group_increase":
        await handle_welcome_message(websocket, group_id, user_id)
        if (sub_type == "invite" or sub_type == "approve") and load_invite_chain_status(
            group_id
        ):
            await save_invite_chain(group_id, user_id, operator_id)
            await send_group_msg(
                websocket,
                group_id,
                f"已记录 [CQ:at,qq={user_id}] 的邀请链，邀请者为 [CQ:at,qq={operator_id}] ，请勿在群内发送违规信息",
            )

    if msg["notice_type"] == "group_decrease":
        await handle_farewell_message(websocket, group_id, user_id, sub_type)


async def handle_group_message(websocket, msg):
    try:
        user_id = msg["user_id"]
        group_id = msg["group_id"]
        raw_message = msg["raw_message"]
        role = msg["sender"]["role"]
        message_id = int(msg["message_id"])

        is_admin = await is_group_admin(role)
        is_owner = await is_group_owner(role)
        is_authorized = (is_admin or is_owner) or (user_id in owner_id)

        if (
            raw_message == "群管系统"
            or raw_message == "group_manager"
            and is_authorized
        ):
            await show_menu(websocket, group_id)

        if is_authorized and (raw_message == "测试" or raw_message == "test"):
            logging.info("收到管理员的测试消息。")
            if raw_message == "测试":
                await send_group_msg(websocket, group_id, "测试成功")
            elif raw_message == "test":
                await send_group_msg(websocket, group_id, "Test successful")

        if raw_message == "全员禁言" or raw_message == "mute_all" and is_authorized:
            await set_group_whole_ban(websocket, group_id, True)

        if raw_message == "全员解禁" or raw_message == "unmute_all" and is_authorized:
            await set_group_whole_ban(websocket, group_id, False)

        if is_authorized and (
            re.match(r"kick.*", raw_message)
            or re.match(r"t.*", raw_message)
            or re.match(r"踢.*", raw_message)
        ):
            kick_qq = None
            for i, item in enumerate(msg["message"]):
                if item["type"] == "at":
                    kick_qq = item["data"]["qq"]
                    break
            if kick_qq:
                await set_group_kick(websocket, group_id, kick_qq)

        if re.match(r"ban.*", raw_message):
            if raw_message == "banme" or raw_message == "禁言我":
                await banme_random_time(websocket, group_id, user_id)
            if (
                re.match(r"ban.*", raw_message) or re.match(r"禁言.*", raw_message)
            ) and is_authorized:
                await ban_user(websocket, group_id, msg["message"])
            if (
                raw_message == "banrandom" or raw_message == "随机禁言"
            ) and is_authorized:
                await ban_random_user(websocket, group_id, msg["message"])

        if (
            re.match(r"unban.*", raw_message) or re.match(r"解禁.*", raw_message)
        ) and is_authorized:
            await unban_user(websocket, group_id, msg["message"])

        if "recall" in raw_message or "撤回" in raw_message and is_authorized:
            message_id = int(msg["message"][0]["data"]["id"])
            await delete_msg(websocket, message_id)

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

        if raw_message.startswith("view_invite_chain ") or raw_message.startswith(
            "查看邀请链 "
        ):
            target_user_id = raw_message.split(" ", 1)[1].strip()
            await view_invite_chain(websocket, group_id, target_user_id)

        if is_authorized:
            if raw_message == "enable_video_check" or raw_message == "开启视频检测":
                if load_status(group_id, "video_check_status"):
                    await send_group_msg(
                        websocket, group_id, "视频检测已经开启了，无需重复开启。"
                    )
                else:
                    save_status(group_id, "video_check_status", True)
                    await send_group_msg(websocket, group_id, "已开启视频检测。")
            elif raw_message == "disable_video_check" or raw_message == "关闭视频检测":
                if not load_status(group_id, "video_check_status"):
                    await send_group_msg(
                        websocket, group_id, "视频检测已经关闭了，无需重复关闭。"
                    )
                else:
                    save_status(group_id, "video_check_status", False)
                    await send_group_msg(websocket, group_id, "已关闭视频检测。")

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

        # 前面执行完所有命令之后，检查违禁词
        if await check_banned_words(websocket, group_id, msg):
            return

    except Exception as e:
        logging.error(f"处理群消息时出错: {e}")
