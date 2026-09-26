package com.attribution.interfaces.dto.kline;

import com.attribution.domain.entity.TechKlineDailyEntity;
import com.fasterxml.jackson.annotation.JsonInclude;
import com.fasterxml.jackson.annotation.JsonProperty;
import lombok.AllArgsConstructor;
import lombok.Builder;
import lombok.Data;
import lombok.NoArgsConstructor;

import java.time.LocalDate;

/**
 * 日 K 线响应 VO
 * <p>
 * 前端约定所有字段均为 snake_case，因此本 VO 用 {@link JsonProperty} 显式声明。
 * 这样既不破坏 Java 端 camelCase 命名，也保证 API 输出兼容旧 Python 工程。
 */
@Data
@Builder
@NoArgsConstructor
@AllArgsConstructor
@JsonInclude(JsonInclude.Include.ALWAYS)
public class KlineVO {

    @JsonProperty("date")
    private LocalDate date;

    @JsonProperty("symbol")
    private String symbol;

    @JsonProperty("name")
    private String name;

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

    @JsonProperty("change_pct")
    private Double changePct;

    // ── MA ─────────────────────────────────
    @JsonProperty("ma5")
    private Double ma5;

    @JsonProperty("ma10")
    private Double ma10;

    @JsonProperty("ma20")
    private Double ma20;

    @JsonProperty("ma60")
    private Double ma60;

    // ── EMA ────────────────────────────────
    @JsonProperty("ema12")
    private Double ema12;

    @JsonProperty("ema26")
    private Double ema26;

    // ── MACD ───────────────────────────────
    @JsonProperty("macd_dif")
    private Double macdDif;

    @JsonProperty("macd_dea")
    private Double macdDea;

    @JsonProperty("macd_bar")
    private Double macdBar;

    // ── RSI ────────────────────────────────
    @JsonProperty("rsi6")
    private Double rsi6;

    @JsonProperty("rsi12")
    private Double rsi12;

    @JsonProperty("rsi24")
    private Double rsi24;

    // ── KDJ ────────────────────────────────
    @JsonProperty("kdj_k")
    private Double kdjK;

    @JsonProperty("kdj_d")
    private Double kdjD;

    @JsonProperty("kdj_j")
    private Double kdjJ;

    // ── BOLL ───────────────────────────────
    @JsonProperty("boll_up")
    private Double bollUp;

    @JsonProperty("boll_mid")
    private Double bollMid;

    @JsonProperty("boll_dn")
    private Double bollDn;

    public static KlineVO fromEntity(TechKlineDailyEntity e) {
        return KlineVO.builder()
            .date(e.getDate())
            .symbol(e.getSymbol())
            .name(e.getName())
            .open(e.getOpen())
            .high(e.getHigh())
            .low(e.getLow())
            .close(e.getClose())
            .volume(e.getVolume())
            .amount(e.getAmount())
            .changePct(e.getChangePct())
            .ma5(e.getMa5())
            .ma10(e.getMa10())
            .ma20(e.getMa20())
            .ma60(e.getMa60())
            .ema12(e.getEma12())
            .ema26(e.getEma26())
            .macdDif(e.getMacdDif())
            .macdDea(e.getMacdDea())
            .macdBar(e.getMacdBar())
            .rsi6(e.getRsi6())
            .rsi12(e.getRsi12())
            .rsi24(e.getRsi24())
            .kdjK(e.getKdjK())
            .kdjD(e.getKdjD())
            .kdjJ(e.getKdjJ())
            .bollUp(e.getBollUp())
            .bollMid(e.getBollMid())
            .bollDn(e.getBollDn())
            .build();
    }
}
