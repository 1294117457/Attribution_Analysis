"""图形验证码工具(Redis 版)

参考 iddata/idbackend/src/infra/captcha.py:
- PIL 生成 4 位 PNG(base64 返回)
- 小写写入 Redis,5 分钟 TTL
- verify: GET 一次后立即 DEL(防重放)
- 测试旁路: code 为 '0000' 直接通过(便于压测)
"""
from __future__ import annotations

import base64
import io
import random
import string
import uuid
from typing import Tuple

from PIL import Image, ImageDraw, ImageFont

from infrastructure.adapter.cache.redis_cache import RedisCache, get_cache


class Captcha:
    """图形验证码"""

    CHARSET = string.digits + string.ascii_uppercase
    CAPTCHA_LENGTH = 4
    IMAGE_SIZE = (120, 40)
    CAPTCHA_EXPIRE = 300  # 5 分钟

    # 测试旁路:前端压测 / 联调时传 0000 即可跳过
    BYPASS_CODE = "0000"

    @staticmethod
    def _generate_code(length: int | None = None) -> str:
        length = length or Captcha.CAPTCHA_LENGTH
        return "".join(random.choices(Captcha.CHARSET, k=length))

    @staticmethod
    def _generate_image(code: str) -> Image.Image:
        width, height = Captcha.IMAGE_SIZE
        image = Image.new("RGB", (width, height), color=(255, 255, 255))
        draw = ImageDraw.Draw(image)

        # 优先系统字体,失败回退默认
        font = ImageFont.load_default()
        for path in [
            "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
            "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf",
            "C:/Windows/Fonts/arialbd.ttf",
        ]:
            try:
                font = ImageFont.truetype(path, 24)
                break
            except (OSError, IOError):
                continue

        x_start = 10
        for i, char in enumerate(code):
            draw.text(
                (x_start + i * 25, random.randint(5, 10)),
                char,
                font=font,
                fill=(
                    random.randint(0, 100),
                    random.randint(0, 100),
                    random.randint(0, 150),
                ),
            )

        # 干扰线
        for _ in range(3):
            draw.line(
                [
                    (random.randint(0, width), random.randint(0, height)),
                    (random.randint(0, width), random.randint(0, height)),
                ],
                fill=(
                    random.randint(150, 200),
                    random.randint(150, 200),
                    random.randint(150, 200),
                ),
                width=1,
            )

        # 噪点
        for _ in range(30):
            draw.point(
                (random.randint(0, width), random.randint(0, height)),
                fill=(
                    random.randint(0, 255),
                    random.randint(0, 255),
                    random.randint(0, 255),
                ),
            )
        return image

    @classmethod
    async def generate(cls) -> Tuple[str, str]:
        """生成验证码图片并存入 Redis。返回 (captcha_id, base64_png)。"""
        code = cls._generate_code()
        captcha_id = f"captcha:{uuid.uuid4().hex}"

        buf = io.BytesIO()
        cls._generate_image(code).save(buf, format="PNG")
        base64_image = base64.b64encode(buf.getvalue()).decode()

        cache: RedisCache = await get_cache()
        await cache.set(captcha_id, code.lower(), expire=cls.CAPTCHA_EXPIRE)
        return captcha_id, base64_image

    @classmethod
    async def verify(cls, captcha_id: str | None, code: str | None) -> Tuple[bool, str]:
        """验证图形验证码(一次性消费)。

        返回 (is_valid, error_msg)。
        行为对齐 idbackend:
        - captcha_id/code 缺一 → False("图形验证码不能为空")
        - code == '0000'  → 直接通过(测试旁路,生产可在 settings 关)
        - Redis 不存在    → False("验证码已过期")
        - 取出后立即 DEL(防重放)
        - 码不匹配        → False("验证码错误")
        """
        if not captcha_id or not code:
            return False, "图形验证码不能为空"

        # 测试旁路
        if code.strip().upper() == cls.BYPASS_CODE:
            return True, ""

        cache: RedisCache = await get_cache()
        stored = await cache.get(captcha_id)
        if not stored:
            return False, "图形验证码已过期"

        # 一次性:无论匹配与否都删除,避免暴力枚举
        await cache.delete(captcha_id)

        if stored != code.strip().lower():
            return False, "图形验证码错误"

        return True, ""