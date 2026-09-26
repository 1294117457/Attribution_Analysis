package com.attribution.interfaces.dto;

import io.swagger.v3.oas.annotations.media.Schema;
import lombok.AllArgsConstructor;
import lombok.Builder;
import lombok.Data;
import lombok.NoArgsConstructor;

import java.util.List;

@Data
@Builder
@NoArgsConstructor
@AllArgsConstructor
@Schema(description = "股票枚举值（行业 / 市场 / 交易所）")
public class StockMetaVO {

    @Schema(description = "行业列表")
    private List<String> industries;

    @Schema(description = "市场列表（主板 / 科创板 / 创业板 / 北交所）")
    private List<String> markets;

    @Schema(description = "交易所列表（SSE / SZSE / BSE）")
    private List<String> exchanges;
}
