"""全量触发：membership + snapshot + index_th
先 membership（5000+ 股票最慢，30 分钟），同时触发 snapshot（375 个概念，~2 分钟）和 index_th（375 个概念，~3 分钟）
"""
import requests
import time

def trigger(task_type, params=None):
    res = requests.post(
        "http://127.0.0.1:8000/api/v1/collect/tasks",
        json={"task_type": task_type, "params": params or {}},
        timeout=10,
    )
    print(f"=== {task_type} ===")
    print(res.json())
    return res.json()["data"]["task_id"]


# 1. Snapshot（最快，先跑出涨跌染色数据）
sid = trigger("concept_snapshot")
time.sleep(1)
# 2. Index TH
iid = trigger("concept_index_th")
time.sleep(1)
# 3. Membership（最慢，5000+ 股票 ~30 分钟，全量）
mid = trigger("concept_membership")

print()
print(f"已启动: snapshot={sid} index_th={iid} membership={mid}")
