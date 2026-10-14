"""step7 E: 自动生成 14 个 converter 文件

策略：
- 扫描所有 contexts/market/domain/*/bo.py 和 contexts/concept/domain/*/bo.py
- 提取 to_entity() 方法
- 转换为独立函数 <bo_name>_to_entity(bo) -> Entity
- 写到 contexts/<ctx>/application/<entity>/converter.py
"""
import os
import ast
from pathlib import Path

ROOT = Path("D:/codes/Attribution_Analysis/backend/src")


def extract_to_entity_method(bo_path: str, class_name: str) -> str | None:
    """从 bo.py 提取 to_entity() 方法的源码"""
    text = Path(bo_path).read_text(encoding="utf-8")
    try:
        tree = ast.parse(text, bo_path)
    except SyntaxError:
        return None
    for node in ast.walk(tree):
        if isinstance(node, ast.ClassDef) and node.name == class_name:
            for item in node.body:
                if isinstance(item, ast.FunctionDef) and item.name == "to_entity":
                    # 提取该方法的源码
                    lines = text.split("\n")
                    return "\n".join(lines[item.lineno - 1:item.end_lineno])
    return None


def find_bo_files():
    """扫描所有 bo.py"""
    bo_files = []
    for root, dirs, files in os.walk(ROOT / "contexts"):
        for f in files:
            if f == "bo.py":
                bo_files.append(Path(root) / f)
    return bo_files


def get_bo_class_name(bo_path: Path) -> str | None:
    """从 bo.py 提取第一个 BaseModel 类的名字"""
    text = bo_path.read_text(encoding="utf-8")
    tree = ast.parse(text, str(bo_path))
    for node in ast.walk(tree):
        if isinstance(node, ast.ClassDef):
            # 检查是否继承自 BaseModel
            for base in node.bases:
                if isinstance(base, ast.Name) and base.id == "BaseModel":
                    return node.name
    return None


def determine_ctx_and_entity(bo_path: Path) -> tuple[str, str, str]:
    """从 bo_path 推断 context 和 entity 名

    例: contexts/market/domain/kline/bo.py → ("market", "kline")
        contexts/concept/domain/concept/bo.py → ("concept", "concept")
    """
    parts = bo_path.parts
    # 找 contexts/<ctx> 位置
    for i, p in enumerate(parts):
        if p == "contexts" and i + 1 < len(parts):
            ctx = parts[i + 1]
            # 找 domain/<entity> 位置
            for j in range(i + 2, len(parts) - 1):
                if parts[j] == "domain" and j + 1 < len(parts):
                    entity = parts[j + 1]
                    return ctx, entity
    return ("", "")


def build_converter(bo_path: Path, class_name: str, to_entity_src: str) -> str:
    """构造 converter 文件内容"""
    ctx, entity = determine_ctx_and_entity(bo_path)
    func_name = f"{class_name[0].lower() + class_name[1:]}__to_entity" if False else f"{class_name.lower()}_to_entity"

    # 解析 to_entity_src 中的 lazy import，提取 entity 路径
    import re
    m = re.search(r'from\s+([\w.]+)\s+import\s+(\w+)', to_entity_src)
    entity_path = m.group(1) if m else "?"

    # 把 to_entity 内部实现转为独立函数
    # 1. 替换 def to_entity(self) -> def func_name(bo)
    body = to_entity_src
    body = re.sub(r'def\s+to_entity\s*\(\s*self([^)]*)\)\s*->\s*"(\w+)":',
                  f'def {func_name}(bo) -> "{m.group(2) if m else class_name}":',
                  body)
    # 2. 替换 self.X 为 bo.X
    body = re.sub(r'\bself\.', 'bo.', body)
    # 3. 删掉 docstring
    body = re.sub(r'"""[^"]*?"""\s*', '', body)
    # 4. 替换 id=0 参数模式（如果有）
    body = re.sub(r'create\(\s*id=id,', 'create(', body)
    body = re.sub(r'id\s*=\s*id\b', '', body)
    # 5. pop source 等
    body = re.sub(r"args\.pop\(['\"]source['\"]\)", "# source 字段已被 KlineBO 过滤", body)

    header = f'''"""{entity} BO → Entity 转换器（step7-e）

从 contexts/{ctx}/domain/{entity}/bo.py 的 to_entity() 方法抽离而来。
调用方应用：{func_name}(bo_instance) -> Entity_instance
"""
from __future__ import annotations


'''
    return header + body.strip() + "\n"


def main():
    print("step7 E: 自动生成 converter")
    print()
    total = 0
    for bo_path in find_bo_files():
        rel = bo_path.relative_to(ROOT)
        ctx, entity = determine_ctx_and_entity(bo_path)
        if not ctx:
            continue
        # 一个 bo.py 可能含多个类（capital 等有 6 个；finance 4 个）
        text = bo_path.read_text(encoding="utf-8")
        tree = ast.parse(text, str(bo_path))
        bo_classes = []
        for node in ast.walk(tree):
            if isinstance(node, ast.ClassDef):
                for base in node.bases:
                    if isinstance(base, ast.Name) and base.id == "BaseModel":
                        bo_classes.append(node.name)
                        break
        if not bo_classes:
            continue

        # 找或建 application/<entity>/converter.py
        converter_dir = ROOT / "contexts" / ctx / "application" / entity
        if entity == "concept":
            converter_dir = ROOT / "contexts" / "concept" / "application" / "concept"
        converter_path = converter_dir / "converter.py"

        body_parts = [f'"""{entity} BO → Entity 转换器（step7-e 自动生成）"""\nfrom __future__ import annotations\n\n']
        for cls_name in bo_classes:
            to_entity_src = extract_to_entity_method(str(bo_path), cls_name)
            if to_entity_src is None:
                continue
            func_name = f"{cls_name[0].lower() + cls_name[1:]}_to_entity"
            # 转 self→bo
            import re
            func_body = to_entity_src
            m = re.search(r'from\s+([\w.]+)\s+import\s+(\w+)', func_body)
            if m:
                body_parts.append(f"# {cls_name} → {m.group(2)}")
                body_parts.append(f"from {m.group(1)} import {m.group(2)}")
                body_parts.append("")
            # 把 to_entity(self) → func_name(bo)
            func_body = re.sub(r'def\s+to_entity\s*\(\s*self([^)]*)\)\s*->\s*"(\w+)":',
                              f'def {func_name}(bo) -> "{m.group(2) if m else cls_name}":',
                              func_body)
            # self.X → bo.X
            func_body = re.sub(r'\bself\.', 'bo.', func_body)
            # id=id,  → （删了）
            func_body = re.sub(r',\s*id\s*=\s*id', '', func_body)
            func_body = re.sub(r'\bid\s*=\s*id\b', '', func_body)
            # 删 docstring
            func_body = re.sub(r'"""[^"]*?"""\s*', '', func_body)
            # pop source 注释
            func_body = re.sub(r'# source 字段已被 KlineBO 过滤', '', func_body)
            body_parts.append(func_body.strip())
            body_parts.append("")
            body_parts.append("")
            total += 1

        converter_dir.mkdir(parents=True, exist_ok=True)
        converter_path.write_text("\n".join(body_parts), encoding="utf-8")
        print(f"  GEN: {converter_path.relative_to(ROOT)}  ({len(bo_classes)} converters)")

    print(f"\n  共生成 {total} 个转换函数")


if __name__ == "__main__":
    main()
