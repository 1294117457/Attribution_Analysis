package com.attribution.market.converter;

import java.util.List;

import com.attribution.market.entity.*;
import com.attribution.market.vo.*;

/** 数据看板 PO → VO 转换器 */
public final class DataBoardConverter {

    private DataBoardConverter() {
    }

    // ── 技术面 ───────────────────────────────────────────────

    public static AdjFactorVO toVO(AdjFactorPO po) {
        if (po == null) return null;
        AdjFactorVO vo = new AdjFactorVO();
        vo.setTradeDate(po.getTradeDate());
        vo.setAdjFactor(po.getAdjFactor());
        return vo;
    }

    public static SuspendEventVO toVO(SuspendPO po) {
        if (po == null) return null;
        SuspendEventVO vo = new SuspendEventVO();
        vo.setTradeDate(po.getTradeDate());
        vo.setSuspendTiming(po.getSuspendTiming());
        vo.setSuspendType(po.getSuspendType());
        return vo;
    }

    public static NameChangeVO toVO(NameChangePO po) {
        if (po == null) return null;
        NameChangeVO vo = new NameChangeVO();
        vo.setName(po.getName());
        vo.setStartDate(po.getStartDate());
        vo.setEndDate(po.getEndDate());
        vo.setAnnDate(po.getAnnDate());
        vo.setChangeReason(po.getChangeReason());
        return vo;
    }

    // ── 资金面 ───────────────────────────────────────────────

    public static MoneyflowDayVO toVO(MoneyflowPO po) {
        if (po == null) return null;
        MoneyflowDayVO vo = new MoneyflowDayVO();
        vo.setTradeDate(po.getTradeDate());
        vo.setBuySmAmount(po.getBuySmAmount());
        vo.setSellSmAmount(po.getSellSmAmount());
        vo.setBuyMdAmount(po.getBuyMdAmount());
        vo.setSellMdAmount(po.getSellMdAmount());
        vo.setBuyLgAmount(po.getBuyLgAmount());
        vo.setSellLgAmount(po.getSellLgAmount());
        vo.setBuyElgAmount(po.getBuyElgAmount());
        vo.setSellElgAmount(po.getSellElgAmount());
        vo.setNetMfAmount(po.getNetMfAmount());
        vo.setNetMfVol(po.getNetMfVol());
        return vo;
    }

    public static MarginDayVO toVO(MarginDetailPO po) {
        if (po == null) return null;
        MarginDayVO vo = new MarginDayVO();
        vo.setTradeDate(po.getTradeDate());
        vo.setRzye(po.getRzye());
        vo.setRqye(po.getRqye());
        vo.setRzrqye(po.getRzrqye());
        vo.setRzmre(po.getRzmre());
        vo.setRzche(po.getRzche());
        vo.setRqyl(po.getRqyl());
        vo.setRqmcl(po.getRqmcl());
        vo.setRqchl(po.getRqchl());
        return vo;
    }

    public static TopListRowVO toVO(TopListPO po) {
        if (po == null) return null;
        TopListRowVO vo = new TopListRowVO();
        vo.setTradeDate(po.getTradeDate());
        vo.setName(po.getName());
        vo.setClose(po.getClose());
        vo.setPctChange(po.getPctChange());
        vo.setTurnoverRate(po.getTurnoverRate());
        vo.setAmount(po.getAmount());
        vo.setLBuy(po.getLBuy());
        vo.setLSell(po.getLSell());
        vo.setLAmount(po.getLAmount());
        vo.setNetAmount(po.getNetAmount());
        vo.setNetRate(po.getNetRate());
        vo.setAmountRate(po.getAmountRate());
        vo.setFloatValues(po.getFloatValues());
        vo.setReason(po.getReason());
        return vo;
    }

    public static TopInstRowVO toVO(TopInstPO po) {
        if (po == null) return null;
        TopInstRowVO vo = new TopInstRowVO();
        vo.setTradeDate(po.getTradeDate());
        vo.setExalter(po.getExalter());
        vo.setSide(po.getSide());
        vo.setBuy(po.getBuy());
        vo.setBuyRate(po.getBuyRate());
        vo.setSell(po.getSell());
        vo.setSellRate(po.getSellRate());
        vo.setNetBuy(po.getNetBuy());
        vo.setReason(po.getReason());
        return vo;
    }

    public static BlockTradeRowVO toVO(BlockTradePO po) {
        if (po == null) return null;
        BlockTradeRowVO vo = new BlockTradeRowVO();
        vo.setTradeDate(po.getTradeDate());
        vo.setName(po.getName());
        vo.setPrice(po.getPrice());
        vo.setVol(po.getVol());
        vo.setAmount(po.getAmount());
        vo.setBuyer(po.getBuyer());
        vo.setSeller(po.getSeller());
        return vo;
    }

    public static HolderNumRowVO toVO(HolderNumPO po) {
        if (po == null) return null;
        HolderNumRowVO vo = new HolderNumRowVO();
        vo.setEndDate(po.getEndDate());
        vo.setAnnDate(po.getAnnDate());
        vo.setHolderNum(po.getHolderNum());
        vo.setHolderNums(po.getHolderNums());
        return vo;
    }

    // ── 基本面 ───────────────────────────────────────────────

    public static ValuationRowVO toVO(DailyBasicPO po) {
        if (po == null) return null;
        ValuationRowVO vo = new ValuationRowVO();
        vo.setTradeDate(po.getTradeDate());
        vo.setClose(po.getClose());
        vo.setTurnoverRate(po.getTurnoverRate());
        vo.setTurnoverRateF(po.getTurnoverRateF());
        vo.setVolumeRatio(po.getVolumeRatio());
        vo.setPe(po.getPe());
        vo.setPeTtm(po.getPeTtm());
        vo.setPb(po.getPb());
        vo.setPs(po.getPs());
        vo.setPsTtm(po.getPsTtm());
        vo.setDvRatio(po.getDvRatio());
        vo.setDvTtm(po.getDvTtm());
        vo.setTotalShare(po.getTotalShare());
        vo.setFloatShare(po.getFloatShare());
        vo.setTotalMv(po.getTotalMv());
        vo.setCircMv(po.getCircMv());
        return vo;
    }

    public static FinReportRowVO toVO(FinReportPO po) {
        if (po == null) return null;
        FinReportRowVO vo = new FinReportRowVO();
        vo.setEndDate(po.getEndDate());
        vo.setAnnDate(po.getAnnDate());
        vo.setReportType(po.getReportType());
        vo.setBasicEps(po.getBasicEps());
        vo.setDilutedEps(po.getDilutedEps());
        vo.setTotalRevenue(po.getTotalRevenue());
        vo.setRevenue(po.getRevenue());
        vo.setOperateProfit(po.getOperateProfit());
        vo.setTotalProfit(po.getTotalProfit());
        vo.setNIncome(po.getNIncome());
        vo.setNIncomeAttrP(po.getNIncomeAttrP());
        vo.setNetMargin(calculateNetMargin(po.getNIncome(), po.getRevenue()));
        return vo;
    }

    /** 净利率（%），保留两位小数 */
    public static Double calculateNetMargin(Double netIncome, Double revenue) {
        if (netIncome == null || revenue == null || revenue == 0) return null;
        return Math.round(netIncome / revenue * 10000.0) / 100.0;
    }

    /** 净利率（%）：从 PO 的 BigDecimal 字段计算 */
    public static Double calculateNetMargin(
            java.math.BigDecimal netIncome, java.math.BigDecimal revenue) {
        if (netIncome == null || revenue == null || revenue.signum() == 0) return null;
        return Math.round(netIncome.doubleValue() / revenue.doubleValue() * 10000.0) / 100.0;
    }

    public static Top10HolderRowVO toVO(Top10HolderPO po) {
        if (po == null) return null;
        Top10HolderRowVO vo = new Top10HolderRowVO();
        vo.setEndDate(po.getEndDate());
        vo.setAnnDate(po.getAnnDate());
        vo.setHolderName(po.getHolderName());
        vo.setHoldAmount(po.getHoldAmount());
        vo.setHoldRatio(po.getHoldRatio());
        vo.setHoldFloatRatio(po.getHoldFloatRatio());
        vo.setHoldChange(po.getHoldChange());
        vo.setHolderType(po.getHolderType());
        return vo;
    }

    public static Top10FloatRowVO toVO(Top10FloatPO po) {
        if (po == null) return null;
        Top10FloatRowVO vo = new Top10FloatRowVO();
        vo.setEndDate(po.getEndDate());
        vo.setAnnDate(po.getAnnDate());
        vo.setHolderName(po.getHolderName());
        vo.setHoldAmount(po.getHoldAmount());
        vo.setHoldRatio(po.getHoldRatio());
        vo.setHoldChange(po.getHoldChange());
        vo.setHolderType(po.getHolderType());
        return vo;
    }

    public static DividendRowVO toVO(DividendPO po) {
        if (po == null) return null;
        DividendRowVO vo = new DividendRowVO();
        vo.setEndDate(po.getEndDate());
        vo.setAnnDate(po.getAnnDate());
        vo.setRecordDate(po.getRecordDate());
        vo.setExDate(po.getExDate());
        vo.setPayDate(po.getPayDate());
        vo.setDivProc(po.getDivProc());
        vo.setStkDiv(po.getStkDiv());
        vo.setStkBoRate(po.getStkBoRate());
        vo.setStkCoRate(po.getStkCoRate());
        vo.setCashDiv(po.getCashDiv());
        vo.setCashDivTax(po.getCashDivTax());
        return vo;
    }

    // ── 批量转换 ─────────────────────────────────────────────

    public static List<AdjFactorVO> toAdjFactorList(List<AdjFactorPO> pos) {
        return pos == null ? List.of() : pos.stream().map(DataBoardConverter::toVO).toList();
    }

    public static List<SuspendEventVO> toSuspendList(List<SuspendPO> pos) {
        return pos == null ? List.of() : pos.stream().map(DataBoardConverter::toVO).toList();
    }

    public static List<NameChangeVO> toNameChangeList(List<NameChangePO> pos) {
        return pos == null ? List.of() : pos.stream().map(DataBoardConverter::toVO).toList();
    }

    public static List<MoneyflowDayVO> toMoneyflowList(List<MoneyflowPO> pos) {
        return pos == null ? List.of() : pos.stream().map(DataBoardConverter::toVO).toList();
    }

    public static List<MarginDayVO> toMarginList(List<MarginDetailPO> pos) {
        return pos == null ? List.of() : pos.stream().map(DataBoardConverter::toVO).toList();
    }

    public static List<TopListRowVO> toTopListList(List<TopListPO> pos) {
        return pos == null ? List.of() : pos.stream().map(DataBoardConverter::toVO).toList();
    }

    public static List<TopInstRowVO> toTopInstList(List<TopInstPO> pos) {
        return pos == null ? List.of() : pos.stream().map(DataBoardConverter::toVO).toList();
    }

    public static List<BlockTradeRowVO> toBlockTradeList(List<BlockTradePO> pos) {
        return pos == null ? List.of() : pos.stream().map(DataBoardConverter::toVO).toList();
    }

    public static List<HolderNumRowVO> toHolderNumList(List<HolderNumPO> pos) {
        return pos == null ? List.of() : pos.stream().map(DataBoardConverter::toVO).toList();
    }

    public static List<ValuationRowVO> toValuationList(List<DailyBasicPO> pos) {
        return pos == null ? List.of() : pos.stream().map(DataBoardConverter::toVO).toList();
    }

    public static List<FinReportRowVO> toFinReportList(List<FinReportPO> pos) {
        return pos == null ? List.of() : pos.stream().map(DataBoardConverter::toVO).toList();
    }

    public static List<Top10HolderRowVO> toTop10HolderList(List<Top10HolderPO> pos) {
        return pos == null ? List.of() : pos.stream().map(DataBoardConverter::toVO).toList();
    }

    public static List<Top10FloatRowVO> toTop10FloatList(List<Top10FloatPO> pos) {
        return pos == null ? List.of() : pos.stream().map(DataBoardConverter::toVO).toList();
    }

    public static List<DividendRowVO> toDividendList(List<DividendPO> pos) {
        return pos == null ? List.of() : pos.stream().map(DataBoardConverter::toVO).toList();
    }
}
