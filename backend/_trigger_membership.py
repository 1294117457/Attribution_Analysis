"""触发 concept_membership 测试任务"""
import requests

res = requests.post(
    "http://127.0.0.1:8000/api/v1/collect/tasks",
    json={"task_type": "concept_membership", "params": {"limit": 3}},
    timeout=10,
)
print("status:", res.status_code)
print(res.text[:500])
