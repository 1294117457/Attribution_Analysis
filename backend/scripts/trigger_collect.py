"""按依赖顺序触发概念采集任务并等待完成（需先启动后端服务）

用法：
    python scripts/trigger_collect.py                               # 全链路：清单 → 日 K → 快照 → 成分股 → 入选理由
    python scripts/trigger_collect.py concept_membership --limit 3  # 单个任务，小批量测试
    python scripts/trigger_collect.py concept_index_th --param full=true
    python scripts/trigger_collect.py --no-wait concept_snapshot    # 只触发不等待
    python scripts/trigger_collect.py --force-cancel-stale ...      # 先强制取消同类型残留的 running 任务

任务依赖：concept → concept_index_th → concept_snapshot；concept → concept_membership → concept_reason
"""
import argparse
import time

import requests

DEFAULT_TASKS = ["concept", "concept_index_th", "concept_snapshot", "concept_membership", "concept_reason"]
POLL_SECONDS = 5


def _data(res: requests.Response) -> dict:
    try:
        return res.json().get("data") or {}
    except ValueError:
        return {"message": res.text[:500]}


def cancel_stale(base_url: str, task_type: str) -> None:
    res = requests.get(
        f"{base_url}/api/v1/collect/tasks",
        params={"task_type": task_type, "status": "running"},
        timeout=10,
    )
    for t in _data(res).get("items", []):
        requests.post(f"{base_url}/api/v1/collect/tasks/{t['id']}/cancel", params={"force": True}, timeout=10)
        print(f"  已强制取消残留任务 {task_type}#{t['id']}")


def trigger(base_url: str, task_type: str, params: dict) -> int | None:
    res = requests.post(
        f"{base_url}/api/v1/collect/tasks",
        json={"task_type": task_type, "params": params},
        timeout=60,
    )
    data = _data(res)
    print(f"=== {task_type} {params or ''} → {data.get('message')}")
    return data.get("task_id")


def wait(base_url: str, task_id: int) -> dict:
    while True:
        try:
            p = _data(requests.get(f"{base_url}/api/v1/collect/tasks/{task_id}/progress", timeout=10))
        except requests.RequestException as e:
            print(f"  轮询失败（服务可能在重载）: {type(e).__name__}，稍后重试", flush=True)
            time.sleep(POLL_SECONDS)
            continue
        print(
            f"  [{p.get('status')}] {p.get('done')}/{p.get('total')} "
            f"成功 {p.get('success')} 失败 {p.get('fail')} 跳过 {p.get('skip')}  {p.get('current', '')}",
            flush=True,
        )
        if p.get("status") not in ("running", "pending"):
            break
        time.sleep(POLL_SECONDS)
    task = _data(requests.get(f"{base_url}/api/v1/collect/tasks/{task_id}", timeout=10))
    print(f"  结束: {task.get('status')}，耗时 {task.get('duration_ms')}ms，{task.get('message')}")
    return task


def _parse_param(kv: str) -> tuple[str, object]:
    k, _, v = kv.partition("=")
    if v.lower() in ("true", "false"):
        return k, v.lower() == "true"
    return k, int(v) if v.isdigit() else v


def main() -> None:
    parser = argparse.ArgumentParser(description="触发概念采集任务")
    parser.add_argument("task_types", nargs="*", default=DEFAULT_TASKS, help="任务类型，默认按依赖顺序跑全部概念任务")
    parser.add_argument("--limit", type=int, help="只采集前 N 个单元（测试用）")
    parser.add_argument("--param", action="append", default=[], help="额外参数 key=value，可重复")
    parser.add_argument("--no-wait", action="store_true", help="只触发不等待（任务会并发执行，不保证依赖顺序）")
    parser.add_argument("--force-cancel-stale", action="store_true", help="触发前强制取消同类型 running 残留任务")
    parser.add_argument("--base-url", default="http://127.0.0.1:8000")
    args = parser.parse_args()

    params = dict(_parse_param(kv) for kv in args.param)
    if args.limit:
        params["limit"] = args.limit

    for task_type in args.task_types:
        if args.force_cancel_stale:
            cancel_stale(args.base_url, task_type)
        task_id = trigger(args.base_url, task_type, params)
        if task_id is None:
            print("  未启动，终止后续任务")
            return
        if not args.no_wait:
            task = wait(args.base_url, task_id)
            if task.get("status") not in ("success", "partial"):
                print("  任务未成功，终止后续任务")
                return


if __name__ == "__main__":
    main()
