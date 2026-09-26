package com.attribution.interfaces.dto.kline;

import com.fasterxml.jackson.annotation.JsonProperty;
import lombok.AllArgsConstructor;
import lombok.Builder;
import lombok.Data;
import lombok.NoArgsConstructor;

/**
 * 分钟 K 线响应 VO
 *
 * <p>与前端 MinuteKline 接口字段对齐（snake_case）。
 */
@Data
@Builder
@NoArgsConstructor
@AllArgsConstructor
public class MinuteKlineVO {

    @JsonProperty("datetime")
    private String datetime;

    @JsonProperty("interval")
    private String interval;

    @JsonProperty("open")
    private Double open;

    @JsonProperty("high")
    private Double high;

    @JsonProperty("low")
    private Double low;

    @JsonProperty("close")
    private Double close;

    @JsonProperty("volume")
    private Long volume;

    @JsonProperty("amount")
    private Double amount;
}
