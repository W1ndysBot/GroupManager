import json
import os

DATA_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data")


def load_status(group_id, key):
    try:
        with open(f"{DATA_DIR}/group_status.json", "r", encoding="utf-8") as f:
            data = json.load(f)
            for group_status in data:
                if group_status["group_id"] == group_id:
                    return group_status.get(key, False)
            return False
    except FileNotFoundError:
        return False


def save_status(group_id, key, status):
    try:
        with open(f"{DATA_DIR}/group_status.json", "r", encoding="utf-8") as f:
            data = json.load(f)
    except FileNotFoundError:
        data = []

    group_found = False
    for group_status in data:
        if group_status["group_id"] == group_id:
            group_status[key] = status
            group_found = True
            break

    if not group_found:
        data.append({"group_id": group_id, key: status})

    with open(f"{DATA_DIR}/group_status.json", "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=4)


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
