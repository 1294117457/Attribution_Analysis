"""Patch missing imports in route/dto/{request,response}/*.py"""
import re
import pathlib
from pathlib import Path

ROOT = Path("D:/codes/Attribution_Analysis/backend/src/route/dto")

HEADER_LINES = [
    "from __future__ import annotations",
    "",
    "from datetime import date, datetime",
    "from typing import List, Literal, Optional",
    "",
    "from pydantic import BaseModel, Field, field_validator",
    "",
]


def needed_block(text: str) -> list[str]:
    """Return headers that are not yet present."""
    add = []
    if "from __future__ import annotations" not in text:
        add.append("from __future__ import annotations")
    needs_pyd = ("BaseModel" in text or "Field(" in text or "field_validator" in text) and not re.search(
        r"^from pydantic", text, re.MULTILINE
    )
    if needs_pyd:
        if "field_validator" in text and "field_validator" not in re.findall(
            r"from pydantic import ([^\\n]+)", text
        )[0:1]:
            add.append("from pydantic import BaseModel, Field, field_validator")
        else:
            add.append("from pydantic import BaseModel, Field")
    if ("Optional[" in text or "Literal[" in text or "List[" in text) and "from typing import" not in text:
        add.append("from typing import List, Literal, Optional")
    elif re.search(r"\bOptional\[", text) and "Optional" not in re.search(
        r"from typing import ([^\n]+)", text
    ).group(1) if re.search(r"from typing import ([^\n]+)", text) else True:
        if re.search(r"from typing import ([^\n]+)", text):
            pass  # leave existing typing import as-is
    if re.search(r"\b(datetime|date)\b", text) and "from datetime import" not in text:
        add.append("from datetime import date, datetime")
    return add


def patch(p: Path) -> bool:
    text = p.read_text(encoding="utf-8")
    if "BaseModel" not in text and "Field(" not in text:
        return False
    # Skip panel.py — handled separately
    if p.name == "panel.py":
        return False
    new_add = needed_block(text)
    if not new_add:
        return False
    # determine insertion point: after shebang/__future__/docstring header
    lines = text.splitlines(keepends=False)
    insert_idx = 0
    for i, ln in enumerate(lines):
        s = ln.strip()
        if not s:
            insert_idx = i + 1
            continue
        if s.startswith("#!") or s.startswith("# -*-"):
            insert_idx = i + 1
            continue
        if s.startswith('"""') or s.startswith("'''"):
            # skip until matching triple-quote on its own line
            quote = s[:3]
            j = i
            if s.count(quote) >= 2 and len(s) > 3:
                # one-line docstring
                insert_idx = i + 1
            else:
                insert_idx = i + 1
                while j < len(lines):
                    j += 1
                    if quote in lines[j]:
                        insert_idx = j + 1
                        break
            continue
        if s.startswith("from __future__ import"):
            insert_idx = i + 1
            continue
        break
    new = lines[:insert_idx] + new_add + [""] + lines[insert_idx:]
    p.write_text("\n".join(new) + "\n", encoding="utf-8")
    print("PATCHED", p)
    return True


count = 0
for p in ROOT.rglob("*.py"):
    if patch(p):
        count += 1
print("---")
print("files patched:", count)
