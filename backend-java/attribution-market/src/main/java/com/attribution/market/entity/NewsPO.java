package com.attribution.market.entity;

import java.math.BigDecimal;
import java.time.LocalDateTime;

import com.baomidou.mybatisplus.annotation.*;

import lombok.Data;

@Data
@TableName("news_article")
public class NewsPO {
    @TableId(type = IdType.AUTO)
    private Integer id;

    @TableField("published_at")
    private LocalDateTime publishedAt;

    private String title;
    private String content;
    private String source;
    private String url;
    private String symbols;
    private BigDecimal sentiment;
    private String category;

    @TableField("data_source")
    private String dataSource;
}
