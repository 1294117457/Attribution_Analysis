"""step7 E (v2): 改进的 converter 生成器"""
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


def find_bo_files():
    bo_files = []
    for root, dirs, files in os.walk(ROOT / "contexts"):
        for f in files:
            if f == "bo.py":
                bo_files.append(Path(root) / f)
    return bo_files


def extract_to_entity_method(bo_path: Path, class_name: str) -> str | None:
    text = bo_path.read_text(encoding="utf-8")
    try:
        tree = ast.parse(text, str(bo_path))
    except SyntaxError:
        return None
    for node in ast.walk(tree):
        if isinstance(node, ast.ClassDef) and node.name == class_name:
            for item in node.body:
                if isinstance(item, ast.FunctionDef) and item.name == "to_entity":
                    lines = text.split("\n")
                    return "\n".join(lines[item.lineno - 1:item.end_lineno])
    return None


def to_snake(name: str) -> str:
    """KlineBO → kline_bo"""
    s1 = re.sub(r'(.)([A-Z][a-z]+)', r'\1_\2', name)
    return re.sub(r'([a-z0-9])([A-Z])', r'\1_\2', s1).lower()


def main():
    total = 0
    for bo_path in find_bo_files():
        text = bo_path.read_text(encoding="utf-8")
        try:
            tree = ast.parse(text, str(bo_path))
        except SyntaxError:
            continue
        bo_classes = []
        for node in ast.walk(tree):
            if isinstance(node, ast.ClassDef):
                for base in node.bases:
                    if isinstance(base, ast.Name) and base.id == "BaseModel":
                        bo_classes.append(node.name)
                        break
        if not bo_classes:
            continue

        ctx, entity = determine_ctx_and_entity(bo_path)
        if not ctx:
            continue

        converter_dir = ROOT / "contexts" / ctx / "application" / entity
        converter_path = converter_dir / "converter.py"

        body = [f'"""{entity} BO → Entity 转换器（step7-e 自动生成）"""\nfrom __future__ import annotations\n\n']
        for cls_name in bo_classes:
            to_entity_src = extract_to_entity_method(bo_path, cls_name)
            if to_entity_src is None:
                continue
            m = re.search(r'from\s+([\w.]+)\s+import\s+(\w+)', to_entity_src)
            if not m:
                continue
            entity_module, entity_name = m.group(1), m.group(2)
            func_name = f"{to_snake(cls_name)}_to_entity"
            # 重要：把 create(, kwargs) 修成 create(kwargs)
            body.append(f"# {cls_name} → {entity_name}")
            body.append(f"from {entity_module} import {entity_name}\n")

            # 提取方法体（去掉 def 行和缩进调整）
            lines = to_entity_src.split("\n")
            # 找到函数体第一行
            body_lines = []
            in_method = False
            for line in lines[1:]:  # 跳过 def 行
                if not in_method:
                    if line.strip() == "" or line.startswith("    "):
                        # 还在函数体内
                        in_method = True
                    else:
                        continue
                # 调整缩进：原本 8 空格（class 内部 method 内部），改为 4 空格
                if line.startswith("        "):
                    line = line[4:]
                # 替换 self. → bo.
                line = re.sub(r'\bself\.', 'bo.', line)
                # 删 docstring
                line = re.sub(r'"""[^"]*?"""\s*', '', line)
                # 处理 id=id 残留
                line = re.sub(r',?\s*id\s*=\s*id', '', line)
                # 处理 args.pop（KlineBO 专用）
                line = re.sub(r'args\.pop\(["\']source["\']\)', '# source 字段已过滤', line)
                # 处理 create(, xxx) 残留下：清掉开头的 ", "
                line = re.sub(r'\(\s*,\s*', '(', line)
                # 进一步：清理函数调用紧跟换行后的开头的逗号
                if line.lstrip().startswith(','):
                    line = line.replace(',', '', 1)
                if line.strip() == "" and not body_lines:
                    continue
                body_lines.append(line)

            # 把 def 行替换为新签名
            sig = f"def {func_name}(bo) -> \"{entity_name}\":"
            if body_lines:
                body_lines[0] = sig
            else:
                body_lines = [sig, "    raise NotImplementedError"]

            body.append("\n".join(body_lines))
            body.append("")
            body.append("")
            total += 1

        converter_dir.mkdir(parents=True, exist_ok=True)
        converter_path.write_text("\n".join(body), encoding="utf-8")
        print(f"  GEN: {converter_path.relative_to(ROOT)}  ({len(bo_classes)} funcs)")

    print(f"\n  共生成 {total} 个转换函数")


if __name__ == "__main__":
    main()
