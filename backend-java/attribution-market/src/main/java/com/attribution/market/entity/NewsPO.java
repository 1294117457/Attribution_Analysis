package com.attribution.market.entity;

import java.time.LocalDateTime;

import com.baomidou.mybatisplus.annotation.*;

import lombok.Data;

/**
 * 新闻文章。
 *
 * <p>表 {@code raw_data.news_article}。
 *
 * <p>⚠️ 字段类型：
 * <ul>
 *   <li>{@code id} 是 {@code bigint} → 用 {@link Long}（用 Integer 有溢出风险）；</li>
 *   <li>{@code sentiment} 是 {@code varchar(16)} → 用 {@link String}
 *       （用 BigDecimal 会抛类型转换异常）；</li>
 *   <li>{@code symbols} 是 {@code varchar(10)[]}（PG 数组）→ MyBatis-Plus 默认 TypeHandler
 *       处理不了，本期用 {@code exist = false} 显式排除，避免误用时报错。
 *       接入该表前必须先实现数组 TypeHandler（见开发文档 §8 遗留项 L5）。</li>
 * </ul>
 */
@Data
@TableName("news_article")
public class NewsPO {
    @TableId(type = IdType.AUTO)
    private Long id;

    @TableField("published_at")
    private LocalDateTime publishedAt;

    private String title;
    private String content;
    private String source;
    private String url;

    /** PG 数组列（varchar(10)[]）—— 当前不映射，见类注释 */
    @TableField(value = "symbols", exist = false)
    private String symbols;

    /** 情绪标签（varchar(16)） */
    private String sentiment;

    private String category;

    @TableField("data_source")
    private String dataSource;
}
