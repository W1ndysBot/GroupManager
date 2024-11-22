import logging
import os
import json


# 获取某群的banme最高记录
def get_ban_records(today):
    file_path = os.path.join(os.path.dirname(__file__), "test.json")
    if os.path.exists(file_path):
        with open(file_path, "r") as f:
            try:
                records = json.load(f)
                if today in records:
                    # 获取当日记录并排序
                    today_records = records[today]
                    sorted_records = sorted(
                        today_records.items(), key=lambda x: x[1], reverse=True
                    )
                    return sorted_records
                else:
                    logging.warning(f"没有找到日期 {today} 的记录。")
                    return []
            except json.JSONDecodeError:
                logging.error(f"JSONDecodeError: 文件 test.json 为空或格式错误。")
                return {}
    else:
        print("文件不存在")
        return {}


# 测试函数
print(get_ban_records("2024-11-22"))
