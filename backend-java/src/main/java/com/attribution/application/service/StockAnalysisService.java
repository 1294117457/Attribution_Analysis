package com.attribution.application.service;

import com.attribution.interfaces.dto.kline.KlineVO;
import com.attribution.interfaces.dto.stock.KlineWithIndicatorVO;
import com.attribution.interfaces.dto.stock.PoolMembershipVO;
import com.attribution.interfaces.dto.stock.StockAnalysisVO;
import com.attribution.interfaces.dto.stock.StockInfoVO;
import com.attribution.interfaces.dto.stock.TechnicalSummaryVO;
import com.attribution.infrastructure.exception.BusinessException;
import org.springframework.http.HttpStatus;
import com.attribution.domain.repository.StockInfoRepository;
import com.attribution.domain.repository.StockPoolMemberRepository;
import com.attribution.domain.repository.StockPoolRepository;
import com.attribution.domain.repository.TechKlineDailyRepository;
import com.attribution.application.service.indicator.SignalDetector;
import com.attribution.application.service.indicator.TechnicalSummary;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import java.time.LocalDate;
import java.time.temporal.ChronoUnit;
import java.util.ArrayList;
import java.util.Collections;
import java.util.List;

@Service
@RequiredArgsConstructor
@Slf4j
public class StockAnalysisService {

    private final StockInfoRepository stockRepository;
    private final TechKlineDailyRepository klineRepository;
    private final StockPoolMemberRepository memberRepository;
    private final StockPoolRepository poolRepository;
    private final SignalDetector signalDetector;

    @Transactional(readOnly = true)
    public StockAnalysisVO build(String symbol, int days) {
        var stockEntity = stockRepository.findBySymbol(symbol)
            .orElseThrow(() -> new BusinessException("stock", "STOCK_NOT_FOUND", "股票不存_ " + symbol, HttpStatus.NOT_FOUND));

        StockInfoVO stockInfo = StockInfoVO.builder()
            .symbol(stockEntity.getSymbol())
            .name(stockEntity.getName())
            .industry(stockEntity.getIndustry())
            .market(stockEntity.getMarket())
            .exchange(stockEntity.getExchange())
            .build();

        LocalDate end = LocalDate.now();
        LocalDate start = end.minus(days, ChronoUnit.DAYS);
        var klinesDesc = klineRepository
            .findBySymbolAndDateBetweenOrderByDateDesc(symbol, start, end);
        if (klinesDesc.isEmpty()) {
            throw new BusinessException("kline", "KLINE_DATA_ERROR",
                "K线数据错_[" + symbol + "]: 暂无 K 线数_ 请先采集（days=" + days + "", HttpStatus.BAD_REQUEST);
        }
        var klinesAsc = new ArrayList<>(klinesDesc);
        Collections.reverse(klinesAsc);

        TechnicalSummary summary = signalDetector.summarize(klinesAsc);
        TechnicalSummaryVO summaryVO = toSummaryVO(summary);

        List<KlineWithIndicatorVO> klineVOs = klinesAsc.stream()
            .map(e -> KlineWithIndicatorVO.fromKlineVO(KlineVO.fromEntity(e)))
            .toList();

        List<Object[]> poolRows = memberRepository.findPoolsBySymbol(symbol);
        List<PoolMembershipVO> pools = new ArrayList<>();
        for (Object[] row : poolRows) {
            Long poolId = (Long) row[0];
            String poolName = (String) row[1];
            pools.add(PoolMembershipVO.builder()
                .poolId(poolId)
                .poolName(poolName)
                .build());
        }

        return StockAnalysisVO.builder()
            .stock(stockInfo)
            .summary(summaryVO)
            .klines(klineVOs)
            .pools(pools)
            .build();
    }

    private TechnicalSummaryVO toSummaryVO(TechnicalSummary s) {
        return TechnicalSummaryVO.builder()
            .latestClose(s.getLatestClose())
            .pctChange1d(s.getPctChange1d())
            .pctChange30d(s.getPctChange30d())
            .maAlignment(s.getMaAlignment())
            .ma5(s.getMa5())
            .ma10(s.getMa10())
            .ma20(s.getMa20())
            .ma60(s.getMa60())
            .ma5AboveMa20(s.getMa5AboveMa20())
            .goldenCrossRecent(s.getGoldenCrossRecent())
            .macdStatus(s.getMacdStatus())
            .macdDif(s.getMacdDif())
            .macdDea(s.getMacdDea())
            .macdBar(s.getMacdBar())
            .rsi6(s.getRsi6())
            .rsiStatus(s.getRsiStatus())
            .kdjK(s.getKdjK())
            .kdjD(s.getKdjD())
            .kdjJ(s.getKdjJ())
            .kdjStatus(s.getKdjStatus())
            .bollUp(s.getBollUp())
            .bollMid(s.getBollMid())
            .bollDn(s.getBollDn())
            .bollPosition(s.getBollPosition())
            .signals(s.getSignals())
            .build();
    }
}
