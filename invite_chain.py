import json
import os
from datetime import datetime
from .group_status import load_status, save_status

DATA_DIR = os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
    "data",
    "GroupManager",
)

from app.api import send_group_msg


def load_invite_chain_status(group_id):
    return load_status(group_id, "invite_chain_status")


def save_invite_chain_status(group_id, status):
    save_status(group_id, "invite_chain_status", status)


def load_invite_chain(group_id):
    try:
        with open(
            f"{DATA_DIR}/invite_chain_{group_id}.json", "r", encoding="utf-8"
        ) as f:
            return json.load(f)
    except FileNotFoundError:
        return []


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


async def save_invite_chain(group_id, user_id, operator_id):
    if not load_invite_chain_status(group_id):
        return

    invite_chain = load_invite_chain(group_id)
    invite_chain.append(
        {
            "user_id": str(user_id),
            "operator_id": str(operator_id),
            "date": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        }
    )

    with open(f"{DATA_DIR}/invite_chain_{group_id}.json", "w", encoding="utf-8") as f:
        json.dump(invite_chain, f, ensure_ascii=False, indent=4)
