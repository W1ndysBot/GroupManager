import logging
import re
import os
import sys
import asyncio

sys.path.append(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
)

from app.scripts.GroupManager.banned_words import *
from app.scripts.GroupManager.group_status import *
from app.scripts.GroupManager.invite_chain import *
from app.scripts.GroupManager.welcome_farewell import *
from app.scripts.GroupManager.group_management import *


from app.api import *
from app.config import owner_id


DATA_DIR = os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
    "data/GroupManager",
)


async def show_menu(websocket, group_id):
    menu_message = """群管系统菜单:
违禁词管理:
- 添加违禁词: add ban word 违禁词 或 添加违禁词 违禁词
- 删除违禁词: rm ban word 违禁词 或 删除违禁词 违禁词
- 查看违禁词列表: list ban words 或 查看违禁词
- 开启违禁词检测: on ban words 或 开启违禁词检测
- 关闭违禁词检测: off ban words 或 关闭违禁词检测

禁言管理:
- 禁言自己随机时间: banme 或 禁言我
- 禁言指定用户: ban @用户 60 或 禁言 @用户 60
- 随机禁言一个用户: banrandom 或 随机禁言
- 解禁指定用户: unban @用户 或 解禁 @用户
- 禁言一个你看着不爽的: banyou@用户

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
- 查看群内所有状态开关情况: view_group_status 或 查看群状态"""
    await asyncio.create_task(send_group_msg(websocket, group_id, menu_message))


async def handle_GroupManager_group_notice(websocket, msg):

    # 使用get函数安全的获取参数，以防不存在导致跳出异常
    operator_id = msg.get("operator_id", "")
    sub_type = msg.get("sub_type", "")
    user_id = msg.get("user_id", "")
    group_id = msg.get("group_id", "")

    if msg["notice_type"] == "group_increase":
        asyncio.create_task(handle_welcome_message(websocket, group_id, user_id))
        if (sub_type == "invite" or sub_type == "approve") and load_invite_chain_status(
            group_id
        ):
            asyncio.create_task(save_invite_chain(group_id, user_id, operator_id))
            asyncio.create_task(
                send_group_msg(
                    websocket,
                    group_id,
                    f"已记录 [CQ:at,qq={user_id}] 的邀请链，操作者为 [CQ:at,qq={operator_id}] ，请勿在群内发送违规信息",
                )
            )

    if msg["notice_type"] == "group_decrease":
        asyncio.create_task(
            handle_farewell_message(websocket, group_id, user_id, sub_type)
        )


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

        if (
            raw_message == "群管系统"
            or raw_message == "group_manager"
            and is_authorized
        ):
            await show_menu(websocket, group_id)

        if is_authorized and (raw_message == "测试" or raw_message == "test"):
            logging.info("收到管理员的测试消息。")
            if raw_message == "测试":
                asyncio.create_task(send_group_msg(websocket, group_id, "测试成功"))
            elif raw_message == "test":
                asyncio.create_task(
                    send_group_msg(websocket, group_id, "Test successful")
                )

        if raw_message == "全员禁言" or raw_message == "banall" and is_authorized:
            asyncio.create_task(set_group_whole_ban(websocket, group_id, True))
            return
        if raw_message == "全员解禁" or raw_message == "unbanall" and is_authorized:
            asyncio.create_task(set_group_whole_ban(websocket, group_id, False))
            return

        if is_authorized and (
            re.match(r"kick.*", raw_message)
            or re.match(r"t.*", raw_message)
            or re.match(r"踢.*", raw_message)
        ):
            kick_qq = None
            kick_qq = next(
                (item["data"]["qq"] for item in msg["message"] if item["type"] == "at"),
                None,
            )

            if kick_qq == self_id:
                asyncio.create_task(send_group_msg(websocket, group_id, "踢我干什么！"))
                return

            if kick_qq:
                asyncio.create_task(set_group_kick(websocket, group_id, kick_qq))

        if re.match(r"ban.*", raw_message):

            # 指定禁言一个人
            if re.match(r"banyou.*", raw_message):

                asyncio.create_task(
                    ban_somebody(websocket, user_id, group_id, msg["message"], self_id)
                )
                return

            if raw_message == "banme" or raw_message == "禁言我":
                asyncio.create_task(banme_random_time(websocket, group_id, user_id))
                return

            if (
                raw_message == "banrandom" or raw_message == "随机禁言"
            ) and is_authorized:
                asyncio.create_task(
                    ban_random_user(websocket, group_id, msg["message"])
                )
                return

            if (
                re.match(r"ban.*", raw_message) or re.match(r"禁言.*", raw_message)
            ) and is_authorized:

                asyncio.create_task(
                    ban_user(websocket, group_id, msg["message"], self_id)
                )

        if (
            re.match(r"unban.*", raw_message) or re.match(r"解禁.*", raw_message)
        ) and is_authorized:
            asyncio.create_task(unban_user(websocket, group_id, msg["message"]))

        if "recall" in raw_message or "撤回" in raw_message and is_authorized:
            message_id = int(msg["message"][0]["data"]["id"])
            asyncio.create_task(delete_msg(websocket, message_id))

        if is_authorized:
            if raw_message.startswith("add ban word ") or raw_message.startswith(
                "添加违禁词 "
            ):
                new_word = raw_message.split(" ", 1)[1].strip()
                banned_words = load_banned_words(group_id)
                if new_word not in banned_words:
                    banned_words.append(new_word)
                    save_banned_words(group_id, banned_words)
                    asyncio.create_task(
                        send_group_msg(websocket, group_id, f"已添加违禁词: {new_word}")
                    )
            elif raw_message.startswith("rm ban word ") or raw_message.startswith(
                "删除违禁词 "
            ):
                remove_word = raw_message.split(" ", 1)[1].strip()
                banned_words = load_banned_words(group_id)
                if remove_word in banned_words:
                    banned_words.remove(remove_word)
                    save_banned_words(group_id, banned_words)
                    asyncio.create_task(
                        send_group_msg(
                            websocket, group_id, f"已删除违禁词: {remove_word}"
                        )
                    )
            elif raw_message == "list ban words" or raw_message == "查看违禁词":
                asyncio.create_task(list_banned_words(websocket, group_id))

        if is_authorized:
            if raw_message == "on ban words" or raw_message == "开启违禁词检测":
                if load_banned_words_status(group_id):
                    asyncio.create_task(
                        send_group_msg(
                            websocket, group_id, "违禁词检测已经开启了，无需重复开启。"
                        )
                    )
                else:
                    save_banned_words_status(group_id, True)
                    asyncio.create_task(
                        send_group_msg(websocket, group_id, "已开启违禁词检测。")
                    )
            elif raw_message == "off ban words" or raw_message == "关闭违禁词检测":
                if not load_banned_words_status(group_id):
                    asyncio.create_task(
                        send_group_msg(
                            websocket, group_id, "违禁词检测已经关闭了，无需重复关闭。"
                        )
                    )
                else:
                    save_banned_words_status(group_id, False)
                    asyncio.create_task(
                        send_group_msg(websocket, group_id, "已关闭违禁词检测。")
                    )

        if is_authorized:
            if raw_message == "enable_welcome_message" or raw_message == "开启入群欢迎":
                if load_welcome_status(group_id):
                    asyncio.create_task(
                        send_group_msg(
                            websocket,
                            group_id,
                            "入群欢迎和退群欢送已经开启了，无需重复开启。",
                        )
                    )
                else:
                    save_welcome_status(group_id, True)
                    asyncio.create_task(
                        send_group_msg(
                            websocket, group_id, "已开启入群欢迎和退群欢送。"
                        )
                    )
            elif (
                raw_message == "disable_welcome_message"
                or raw_message == "关闭入群欢迎"
            ):
                if not load_welcome_status(group_id):
                    asyncio.create_task(
                        send_group_msg(
                            websocket,
                            group_id,
                            "入群欢迎和退群欢送已经关闭了，无需重复关闭。",
                        )
                    )
                else:
                    save_welcome_status(group_id, False)
                    asyncio.create_task(
                        send_group_msg(
                            websocket, group_id, "已关闭入群欢迎和退群欢送。"
                        )
                    )

        if is_authorized:
            if raw_message == "enable_invite_chain" or raw_message == "开启邀请链":
                if load_invite_chain_status(group_id):
                    asyncio.create_task(
                        send_group_msg(
                            websocket,
                            group_id,
                            "邀请链功能已经开启过了，无需重复开启。",
                        )
                    )
                else:
                    save_invite_chain_status(group_id, True)
                    asyncio.create_task(
                        send_group_msg(websocket, group_id, "已开启邀请链功能。")
                    )
            elif raw_message == "disable_invite_chain" or raw_message == "关闭邀请链":
                if not load_invite_chain_status(group_id):
                    asyncio.create_task(
                        send_group_msg(
                            websocket, group_id, "邀请链功能已经关闭了，无需重复关闭。"
                        )
                    )
                else:
                    save_invite_chain_status(group_id, False)
                    asyncio.create_task(
                        send_group_msg(websocket, group_id, "已关闭邀请链功能。")
                    )

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
        await check_banned_words(websocket, group_id, msg)

    except Exception as e:
        logging.error(f"处理群消息时出错: {e}")
