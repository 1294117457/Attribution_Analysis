"""pytest 配置"""

import asyncio
import os
import sys
from pathlib import Path

import pytest
import pytest_asyncio

# 添加 src 到路径
backend_dir = Path(__file__).parent.parent
sys.path.insert(0, str(backend_dir / "src"))

# 确保异步事件循环策略在 Linux 下正确工作
if sys.platform.startswith("linux"):
    asyncio.set_event_loop_policy(asyncio.DefaultEventLoopPolicy())
