package com.attribution.interfaces.dto.stock;

import com.attribution.interfaces.dto.kline.KlineVO;
import lombok.AllArgsConstructor;
import lombok.Builder;
import lombok.Data;
import lombok.NoArgsConstructor;

import java.util.List;

@Data
@Builder
@NoArgsConstructor
@AllArgsConstructor
public class StockAnalysisVO {

    private StockInfoVO stock;
    private TechnicalSummaryVO summary;
    private List<KlineWithIndicatorVO> klines;
    private List<PoolMembershipVO> pools;
}
