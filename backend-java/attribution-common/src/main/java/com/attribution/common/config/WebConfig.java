package com.attribution.common.config;

import java.util.List;

import org.springframework.beans.factory.annotation.Value;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;
import org.springframework.web.filter.ShallowEtagHeaderFilter;
import org.springframework.web.servlet.config.annotation.CorsRegistry;
import org.springframework.web.servlet.config.annotation.WebMvcConfigurer;

/**
 * Web 层配置（CORS + ETag）。
 *
 * <p>规范见 {@code docs/规范文档/横切技术规范/基础设施规范.md}（CORS 与安全）。
 *
 * <p>⚠️ CORS 安全要点：
 * <ul>
 *   <li>本项目鉴权走 {@code Authorization: Bearer <token>} 头，**不使用 Cookie**，
 *       因此 {@code allowCredentials} 保持 {@code false}——开成 {@code true} 会让
 *       「允许任意源 + 允许凭证」变成 CSRF 攻击面</li>
 *   <li>允许的源通过 {@code app.cors.allowed-origins} 配置，**禁止**在生产写死 {@code *}</li>
 *   <li>本地开发前端走 Vite 代理、生产走 nginx 反代，两者都是同源，
 *       CORS 只是兜底，不需要放开全部来源</li>
 * </ul>
 */
@Configuration
public class WebConfig implements WebMvcConfigurer {

    /** 允许的跨域来源（构造器注入，避免字段注入在 @Configuration 中的时序问题） */
    private final List<String> allowedOrigins;

    public WebConfig(
            @Value("${app.cors.allowed-origins:http://localhost:3000,http://127.0.0.1:3000}")
                    List<String> allowedOrigins) {
        this.allowedOrigins = allowedOrigins;
    }

    @Override
    public void addCorsMappings(CorsRegistry registry) {
        registry.addMapping("/api/**")
                .allowedOrigins(allowedOrigins.toArray(String[]::new))
                .allowedMethods("GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS")
                .allowedHeaders("*")
                // 鉴权走 Authorization 头而非 Cookie，关闭凭证可避免「任意源 + 凭证」的 CSRF 攻击面
                .allowCredentials(false)
                .maxAge(3600);
    }

    @Bean
    public ShallowEtagHeaderFilter shallowEtagHeaderFilter() {
        return new ShallowEtagHeaderFilter();
    }
}
