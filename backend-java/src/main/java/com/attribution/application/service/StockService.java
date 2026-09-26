package com.attribution.application.service;

import com.attribution.domain.entity.CapHolderNumEntity;
import com.attribution.domain.entity.FinDailyBasicEntity;
import com.attribution.domain.entity.FinReportEntity;
import com.attribution.domain.entity.FinTop10HolderEntity;
import com.attribution.domain.entity.StockInfoEntity;
import com.attribution.domain.entity.TechKlineDailyEntity;
import com.attribution.domain.repository.CapHolderNumRepository;
import com.attribution.domain.repository.ConceptMemberRepository;
import com.attribution.domain.repository.ConceptRepository;
import com.attribution.domain.repository.FinDailyBasicRepository;
import com.attribution.domain.repository.FinReportRepository;
import com.attribution.domain.repository.FinTop10HolderRepository;
import com.attribution.domain.repository.StockInfoRepository;
import com.attribution.domain.repository.TechKlineDailyRepository;
import com.attribution.interfaces.dto.ConceptBriefVO;
import com.attribution.interfaces.dto.StockDetailVO;
import com.attribution.interfaces.dto.StockFinanceSnapshotVO;
import com.attribution.interfaces.dto.TopHolderVO;
import com.attribution.application.service.indicator.SignalDetector;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.stereotype.Service;

import java.time.LocalDate;
import java.util.List;
import java.util.Optional;

@Slf4j
@Service
@RequiredArgsConstructor
public class StockService {

    private final StockInfoRepository stockInfoRepository;
    private final TechKlineDailyRepository klineRepository;
    private final FinDailyBasicRepository dailyBasicRepository;
    private final FinReportRepository finReportRepository;
    private final FinTop10HolderRepository top10HolderRepository;
    private final CapHolderNumRepository holderNumRepository;
    private final ConceptRepository conceptRepository;
    private final ConceptMemberRepository conceptMemberRepository;
    private final SignalDetector signalDetector;

    public StockDetailVO getStockDetail(String symbol) {
        StockInfoEntity info = stockInfoRepository.findBySymbol(symbol)
            .orElseThrow(() -> new com.attribution.infrastructure.exception.BusinessException(
                "stock", "STOCK_NOT_FOUND", "股票不存在: " + symbol, 404));

        LocalDate lastDate = klineRepository.findLastTradeDate().orElse(LocalDate.now());

        Optional<TechKlineDailyEntity> klineOpt = klineRepository.findBySymbolAndDate(symbol, lastDate);
        Optional<FinDailyBasicEntity> basicOpt = dailyBasicRepository.findBySymbolAndTradeDate(symbol, lastDate);

        List<ConceptBriefVO> concepts = getStockConcepts(symbol);

        TechKlineDailyEntity kline = klineOpt.orElse(null);
        List<String> signals = kline != null ? signalDetector.detect(kline) : List.of();

        return StockDetailVO.builder()
            .symbol(info.getSymbol())
            .name(info.getName())
            .industry(info.getIndustry())
            .market(info.getMarket())
            .listStatus(info.getListStatus())
            .listDate(info.getListDate())
            .tradeDate(kline != null ? kline.getDate() : null)
            .close(kline != null ? kline.getClose() : null)
            .open(kline != null ? kline.getOpen() : null)
            .high(kline != null ? kline.getHigh() : null)
            .low(kline != null ? kline.getLow() : null)
            .preClose(null)  // tech_kline_dailys 表无 pre_close 列
            .change(null)    // tech_kline_dailys 表无 change 列
            .pctChange(kline != null ? kline.getChangePct() : null)
            .volume(kline != null ? kline.getVolume() : null)
            .amount(kline != null ? kline.getAmount() : null)
            .turnoverRate(null)  // tech_kline_dailys 表无 turnover_rate 列
            .pe(basicOpt.map(FinDailyBasicEntity::getPe).orElse(null))
            .peTtm(basicOpt.map(FinDailyBasicEntity::getPeTtm).orElse(null))
            .pb(basicOpt.map(FinDailyBasicEntity::getPb).orElse(null))
            .ps(basicOpt.map(FinDailyBasicEntity::getPs).orElse(null))
            .psTtm(basicOpt.map(FinDailyBasicEntity::getPsTtm).orElse(null))
            .dvRatio(basicOpt.map(FinDailyBasicEntity::getDvRatio).orElse(null))
            .totalMv(basicOpt.map(FinDailyBasicEntity::getTotalMv).orElse(null))
            .circMv(basicOpt.map(FinDailyBasicEntity::getCircMv).orElse(null))
            .concepts(concepts)
            .signals(signals)
            .build();
    }

    public com.attribution.interfaces.dto.StockMetaVO getMeta() {
        java.util.List<String> industries = stockInfoRepository.findAll().stream()
                .map(com.attribution.domain.entity.StockInfoEntity::getIndustry)
                .filter(java.util.Objects::nonNull)
                .distinct().sorted()
                .collect(java.util.stream.Collectors.toList());
        java.util.List<String> markets = stockInfoRepository.findAll().stream()
                .map(com.attribution.domain.entity.StockInfoEntity::getMarket)
                .filter(java.util.Objects::nonNull)
                .distinct().sorted()
                .collect(java.util.stream.Collectors.toList());
        java.util.List<String> exchanges = stockInfoRepository.findAll().stream()
                .map(com.attribution.domain.entity.StockInfoEntity::getExchange)
                .filter(java.util.Objects::nonNull)
                .distinct().sorted()
                .collect(java.util.stream.Collectors.toList());
        return com.attribution.interfaces.dto.StockMetaVO.builder()
                .industries(industries)
                .markets(markets)
                .exchanges(exchanges)
                .build();
    }

    public org.springframework.data.domain.Page<StockInfoEntity> listStocks(
            int page, int pageSize, String industry, String market) {
        org.springframework.data.domain.Pageable pageable =
            org.springframework.data.domain.PageRequest.of(
                Math.max(0, page - 1), Math.min(Math.max(1, pageSize), 500));
        if (industry != null && !industry.isBlank()) {
            return stockInfoRepository.findByIndustry(industry, pageable);
        }
        if (market != null && !market.isBlank()) {
            return stockInfoRepository.findByMarket(market, pageable);
        }
        return stockInfoRepository.findAll(pageable);
    }

    public StockFinanceSnapshotVO getFinanceSnapshot(String symbol) {
        List<FinReportEntity> reports = finReportRepository.findBySymbolOrderByEndDateDesc(symbol);
        FinReportEntity latest = reports.isEmpty() ? null : reports.get(0);

        List<CapHolderNumEntity> holders = holderNumRepository.findBySymbolOrderByEndDateDesc(symbol);
        CapHolderNumEntity latestHolder = holders.isEmpty() ? null : holders.get(0);

        List<FinTop10HolderEntity> topHolders = latest != null
            ? top10HolderRepository.findBySymbolAndEndDate(symbol, latest.getEndDate())
            : List.of();

        return StockFinanceSnapshotVO.builder()
            .symbol(symbol)
            .reportEndDate(latest != null ? latest.getEndDate() : null)
            .basicEps(latest != null ? latest.getBasicEps() : null)
            .totalRevenue(latest != null ? latest.getTotalRevenue() : null)
            .revenue(latest != null ? latest.getRevenue() : null)
            .operateProfit(latest != null ? latest.getOperateProfit() : null)
            .nIncome(latest != null ? latest.getNIncome() : null)
            .nIncomeAttrP(latest != null ? latest.getNIncomeAttrP() : null)
            .totalAssets(latest != null ? latest.getTotalAssets() : null)
            .totalLiab(latest != null ? latest.getTotalLiab() : null)
            .latestHolderNum(latestHolder != null ? latestHolder.getHolderNum() : null)
            .latestHolderDate(latestHolder != null ? latestHolder.getEndDate() : null)
            .topHolders(topHolders.stream().map(h -> TopHolderVO.builder()
                .holderName(h.getHolderName())
                .holderType(h.getHolderType())
                .holdAmount(h.getHoldAmount())
                .holdRatio(h.getHoldRatio())
                .holdFloatRatio(h.getHoldFloatRatio())
                .holdChange(h.getHoldChange())
                .endDate(h.getEndDate())
                .build()).toList())
            .dividends(List.of())
            .build();
    }

    private List<ConceptBriefVO> getStockConcepts(String symbol) {
        List<com.attribution.domain.entity.ConceptMemberEntity> members = conceptMemberRepository.findBySymbol(symbol);
        if (members.isEmpty()) {
            return List.of();
        }
        return conceptRepository.findAllById(
                members.stream().map(com.attribution.domain.entity.ConceptMemberEntity::getConceptId).toList())
            .stream()
            .map(c -> ConceptBriefVO.builder()
                .code(c.getCode())
                .conceptId(c.getCode())
                .name(c.getName())
                .source(c.getSource())
                .build())
            .map(bvo -> (ConceptBriefVO) bvo)
            .collect(java.util.stream.Collectors.toList());
    }
}
