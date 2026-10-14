"""step7 E-final: 把 bo.py 里的 to_entity() 方法体替换为委托给 converter

策略：保留 BO.to_entity() 方法（兼容调用方），方法内部委托给 converter。
"""
import os
import ast
import re
from pathlib import Path

ROOT = Path("D:/codes/Attribution_Analysis/backend/src")


def determine_ctx_and_entity(bo_path: Path) -> tuple[str, str]:
    parts = bo_path.parts
    for i, p in enumerate(parts):
        if p == "contexts" and i + 1 < len(parts):
            ctx = parts[i + 1]
            for j in range(i + 2, len(parts) - 1):
                if parts[j] == "domain" and j + 1 < len(parts):
                    entity = parts[j + 1]
                    return ctx, entity
    return ("", "")


def to_snake(name: str) -> str:
    s1 = re.sub(r'(.)([A-Z][a-z]+)', r'\1_\2', name)
    return re.sub(r'([a-z0-9])([A-Z])', r'\1_\2', s1).lower()


def patch_bo_file(bo_path: Path):
    """把 bo.py 里 to_entity() 改为调用 converter"""
    text = bo_path.read_text(encoding="utf-8")
    original = text
    ctx, entity = determine_ctx_and_entity(bo_path)
    if not ctx:
        return

    # 找所有 class name
    try:
        tree = ast.parse(text, str(bo_path))
    except SyntaxError:
        return
    bo_classes = []
    for node in ast.walk(tree):
        if isinstance(node, ast.ClassDef):
            for base in node.bases:
                if isinstance(base, ast.Name) and base.id == "BaseModel":
                    bo_classes.append(node.name)
                    break

    if not bo_classes:
        return

    # 改写每个类的 to_entity 方法
    new_text = text
    for cls_name in bo_classes:
        func_name = f"{to_snake(cls_name)}_to_entity"
        converter_path = f"contexts.{ctx}.application.{entity}.converter"
        # 找 class {cls_name} 中的 to_entity 方法
        # 用正则： def to_entity(self) -> "Entity":
        pattern = re.compile(
            rf'(    def to_entity\([^)]*\)\s*->\s*"[\w]+":\s*\n)((?:        [^\n]*\n)*)',
            re.MULTILINE
        )

        def repl(m):
            old_signature = m.group(1)
            body = m.group(2)
            # 抽出 entity 名
            ent_match = re.search(r'->\s*"(\w+)"', old_signature)
            entity_name = ent_match.group(1) if ent_match else "Entity"
            # 删掉 import 行
            body = re.sub(r'^\s*from\s+[\w.]+\s+import\s+[\w,]+\s*\n', '', body, flags=re.MULTILINE)
            # 删 docstring 行
            body = re.sub(r'^\s*"""[^"]*?"""\s*\n', '', body, flags=re.MULTILINE)
            # 主体只剩 1 行：return XXX(...)
            # 替换为委托调用
            indent = "    "
            return f'{indent}def to_entity(self) -> "{entity_name}":\n{indent}    """委托给 converter（step7-e）"""\n{indent}    from {converter_path} import {func_name}\n{indent}    return {func_name}(self)\n'

        new_text = pattern.sub(repl, new_text)

    if new_text != original:
        bo_path.write_text(new_text, encoding="utf-8")
        print(f"  PATCH: {bo_path.relative_to(ROOT)}  ({len(bo_classes)} classes)")


def main():
    print("step7 E-final: 改写 bo.py 的 to_entity() 委托给 converter")
    print()
    for root, dirs, files in os.walk(ROOT / "contexts"):
        for f in files:
            if f == "bo.py":
                patch_bo_file(Path(root) / f)


if __name__ == "__main__":
    main()
