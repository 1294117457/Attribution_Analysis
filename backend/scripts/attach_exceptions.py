"""把 git HEAD:backend/src/application/exceptions.py 的异常类按归属追加到聚合 entity.py。

归属规则：
  KlineNotFoundError, KlineDataError, CollectionError, ApplicationError
    → domain.entitys.kline.entity
  StockNotFoundError → domain.entitys.stock_info.entity
  PoolNotFoundError, PoolOperationNotFoundError, CannotDeleteDefaultPoolError,
  DuplicatePoolMemberError, PoolMemberNotFoundError, PoolOperationConflictError
    → domain.entitys.stock_pool.entity
"""
import subprocess
from pathlib import Path

ROOT = Path("D:/codes/Attribution_Analysis")
BACKEND_SRC = ROOT / "backend" / "src"

# 拉取原始 exceptions.py
src_text = subprocess.check_output(
    ["git", "show", "HEAD:backend/src/application/exceptions.py"],
    cwd=str(ROOT),
    text=True,
    encoding="utf-8",
)
# 去掉文件头部注释 + import + 顶级 docstring
body_start = src_text.find("class ApplicationError")
body = src_text[body_start:].rstrip() + "\n"

ATTACH_HEADER = """
# ── 应用层遗留异常（来自 application/exceptions.py，迁移至此） ──

"""


def append_once(target: Path, block: str) -> bool:
    text = target.read_text(encoding="utf-8")
    # 已追加过 → 跳过
    if block.lstrip().splitlines()[0] in text:
        return False
    new_text = text.rstrip() + "\n\n" + ATTACH_HEADER + block
    target.write_text(new_text, encoding="utf-8")
    return True


def extract_classes(body: str, names: list[str]) -> str:
    """从 body 中抽取给定 class（并自动包含 ApplicationError 基类，如果用到了），保留缩进；遇到下一个顶级 class 则停。"""
    lines = body.splitlines()
    out: list[str] = []
    keep = False
    started = False
    need_app = any(n != "ApplicationError" for n in names)
    for ln in lines:
        s = ln.lstrip()
        if s.startswith("class "):
            cls = s.split("class ", 1)[1].split("(", 1)[0]
            if cls in names:
                keep = True
                started = True
                out.append(ln)
                continue
            elif started:
                keep = False
        if keep and not started:
            continue
        if keep and started:
            out.append(ln)
    result = "\n".join(out).rstrip() + "\n"
    # 如果需要的子类引用了 ApplicationError，并且结果里没有它的定义，则把它追加在末尾
    if need_app and "class ApplicationError(" not in result and "ApplicationError" in result:
        # 找到 ApplicationError 类的完整定义（使用 lines 重新切）
        app_block_lines: list[str] = []
        app_started = False
        for ln in lines:
            s = ln.lstrip()
            if s.startswith("class ApplicationError"):
                app_started = True
                app_block_lines.append(ln)
                continue
            if app_started:
                # 类结束判定：下一个顶头（无缩进）且不是空行/注释/dedent 的语句
                if ln and not ln.startswith((" ", "\t")) and not ln.lstrip().startswith(("#", "\"\"\"", "'''")):
                    if app_block_lines[-1].rstrip().endswith(":"):
                        pass  # class header line
                    break
                app_block_lines.append(ln)
        result = "\n".join(app_block_lines).rstrip() + "\n\n" + result
    return result


groups = {
    "kline": [
        "ApplicationError",
        "KlineNotFoundError",
        "KlineDataError",
        "CollectionError",
    ],
    "stock_info": ["StockNotFoundError"],
    "stock_pool": [
        "PoolNotFoundError",
        "PoolOperationNotFoundError",
        "CannotDeleteDefaultPoolError",
        "DuplicatePoolMemberError",
        "PoolMemberNotFoundError",
        "PoolOperationConflictError",
    ],
}

for agg, names in groups.items():
    block = extract_classes(body, names)
    if not block.strip():
        print(f"[SKIP] {agg}: no classes extracted")
        continue
    target = BACKEND_SRC / "domain" / "entitys" / agg / "entity.py"
    if not target.exists():
        print(f"[WARN] target missing: {target}")
        continue
    if append_once(target, block):
        print(f"[OK] append {agg}: {names}")
    else:
        print(f"[SKIP] {agg}: already attached")
