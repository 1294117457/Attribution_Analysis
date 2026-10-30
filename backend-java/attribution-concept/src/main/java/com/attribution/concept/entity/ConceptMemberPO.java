package com.attribution.concept.entity;

import java.time.LocalDateTime;

import com.baomidou.mybatisplus.annotation.*;

import lombok.Data;

@Data
@TableName("fundamental_concept_member")
public class ConceptMemberPO {
    private String symbol;

    @TableField("concept_id")
    private Integer conceptId;

    private String reason;

    @TableField("joined_at")
    private LocalDateTime joinedAt;

    @TableField("synced_at")
    private LocalDateTime syncedAt;

    private String source;
}
