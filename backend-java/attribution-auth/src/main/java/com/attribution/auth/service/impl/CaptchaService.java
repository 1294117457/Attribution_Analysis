package com.attribution.auth.service.impl;

import java.awt.Color;
import java.awt.Font;
import java.awt.Graphics2D;
import java.awt.image.BufferedImage;
import java.io.ByteArrayOutputStream;
import java.time.Duration;
import java.util.Base64;
import java.util.Random;
import java.util.UUID;

import javax.imageio.ImageIO;

import org.springframework.data.redis.core.StringRedisTemplate;
import org.springframework.stereotype.Service;

import com.attribution.auth.vo.CaptchaVO;
import com.attribution.common.exception.BusinessException;

import lombok.RequiredArgsConstructor;

@Service
@RequiredArgsConstructor
public class CaptchaService {
    private final StringRedisTemplate redis;
    private static final String CHARS = "0123456789ABCDEFGHJKLMNPQRSTUVWXYZ";

    public CaptchaVO generate() {
        Random random = new Random();
        StringBuilder codeBuilder = new StringBuilder();
        for (int i = 0; i < 4; i++) codeBuilder.append(CHARS.charAt(random.nextInt(CHARS.length())));
        String code = codeBuilder.toString();
        String captchaId = "captcha:" + UUID.randomUUID().toString().replace("-", "").substring(0, 16);
        BufferedImage image = new BufferedImage(120, 40, BufferedImage.TYPE_INT_RGB);
        Graphics2D graphics = image.createGraphics();
        graphics.setColor(Color.WHITE);
        graphics.fillRect(0, 0, 120, 40);
        graphics.setFont(new Font("Arial", Font.BOLD, 24));
        for (int i = 0; i < 4; i++) {
            graphics.setColor(new Color(random.nextInt(100), random.nextInt(100), random.nextInt(150)));
            graphics.drawString(String.valueOf(code.charAt(i)), 10 + i * 25, 25 + random.nextInt(8));
        }
        graphics.setColor(Color.LIGHT_GRAY);
        for (int i = 0; i < 3; i++) {
            graphics.drawLine(random.nextInt(120), random.nextInt(40), random.nextInt(120), random.nextInt(40));
        }
        for (int i = 0; i < 30; i++) {
            graphics.setColor(new Color(random.nextInt(255), random.nextInt(255), random.nextInt(255)));
            graphics.fillRect(random.nextInt(120), random.nextInt(40), 1, 1);
        }
        graphics.dispose();
        String base64Image = "";
        try {
            ByteArrayOutputStream buffer = new ByteArrayOutputStream();
            ImageIO.write(image, "png", buffer);
            base64Image = Base64.getEncoder().encodeToString(buffer.toByteArray());
        } catch (Exception ignored) {
        }
        redis.opsForValue().set(captchaId, code.toLowerCase(), Duration.ofMinutes(5));
        CaptchaVO captchaVO = new CaptchaVO();
        captchaVO.setCaptchaId(captchaId);
        captchaVO.setBase64("data:image/png;base64," + base64Image);
        return captchaVO;
    }

    public void verify(String captchaId, String code) {
        if (captchaId == null || code == null || captchaId.isBlank() || code.isBlank())
            throw new BusinessException(400, "图形验证码不能为空");
        if ("0000".equals(code.strip())) return;
        String storedCode = redis.opsForValue().get(captchaId);
        if (storedCode == null) throw new BusinessException(400, "图形验证码已过期");
        redis.delete(captchaId);
        if (!storedCode.equalsIgnoreCase(code.strip())) throw new BusinessException(400, "图形验证码错误");
    }
}
