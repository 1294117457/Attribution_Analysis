package com.attribution.user.converter;

import java.util.List;
import java.util.Map;

import com.fasterxml.jackson.core.type.TypeReference;
import com.fasterxml.jackson.databind.ObjectMapper;

import com.attribution.market.vo.StockBriefVO;
import com.attribution.user.entity.PoolMemberPO;
import com.attribution.user.entity.PoolOperationPO;
import com.attribution.user.entity.StockPoolPO;
import com.attribution.user.vo.OperationProgressVO;
import com.attribution.user.vo.PoolMemberVO;
import com.attribution.user.vo.PoolOperationVO;
import com.attribution.user.vo.PoolVO;

/**
 * 自选池相关 PO → VO 转换器。
 *
 * <p>池成员需要股票基础信息（名称 / 行业 / 市场 / 交易所），来自关联表，
 * 因此由 Service 查询后以参数形式传入，而非由 PO 自身搬运。
 *
 * <p>规范见 {@code docs/规范文档/纵向分层规范/POJO规范.md} §4。
 *
 * <p><b>为什么是静态工具类而不是 Spring Bean</b>：本项目的 Converter 统一是
 * 「无状态纯函数 + 静态工厂」，见 {@code POJO规范.md} §4.2。
 *
 * <p><b>为什么需要 ObjectMapper 参数</b>：部分字段以 JSON 文本存库，
 * 反序列化需要 {@link ObjectMapper}。**必须传入 Spring 容器管理的实例**
 * （复用全局 Jackson 配置），<b>禁止</b> {@code new ObjectMapper()}——
 * 裸实例不带全局配置（命名策略 / 日期格式 / 未知属性策略 / JavaTimeModule），
 * 序列化结果会与全局约定不一致。
 */
public final class PoolConverter {

    private PoolConverter() {
    }

    /** 池基础视图 */
    public static PoolVO toVO(StockPoolPO po, long memberCount) {
        if (po == null) return null;
        PoolVO vo = new PoolVO();
        vo.setId(po.getId());
        vo.setName(po.getName());
        vo.setPoolType(po.getPoolType());
        vo.setDescription(po.getDescription());
        vo.setColor(po.getColor());
        vo.setIcon(po.getIcon());
        vo.setSortOrder(po.getSortOrder() == null ? 0 : po.getSortOrder());
        vo.setIsDefault(Boolean.TRUE.equals(po.getIsDefault()));
        vo.setIsArchived(Boolean.TRUE.equals(po.getIsArchived()));
        vo.setMemberCount(memberCount);
        vo.setCreatedAt(po.getCreatedAt());
        vo.setUpdatedAt(po.getUpdatedAt());
        return vo;
    }

    /**
     * 池成员视图。
     *
     * @param po 成员 PO
     * @param stockBrief 股票基础信息（symbol → name/industry/market/exchange），可为 null
     */
    public static PoolMemberVO toVO(PoolMemberPO po, Map<String, StockBriefVO> stockBrief) {
        if (po == null) return null;
        PoolMemberVO vo = new PoolMemberVO();
        vo.setSymbol(po.getSymbol());
        vo.setMemo(po.getMemo());
        vo.setSortOrder(po.getSortOrder() == null ? 0 : po.getSortOrder());
        vo.setAddedAt(po.getAddedAt());
        StockBriefVO brief = stockBrief == null ? null : stockBrief.get(po.getSymbol());
        vo.setName(brief == null ? null : brief.getName());
        vo.setIndustry(brief == null ? null : brief.getIndustry());
        vo.setMarket(brief == null ? null : brief.getMarket());
        vo.setExchange(brief == null ? null : brief.getExchange());
        vo.setIsValid(brief != null);
        return vo;
    }

    /**
     * 池操作记录视图。
     *
     * @param po 操作记录 PO
     * @param mapper Spring 管理的 ObjectMapper（用于反序列化 JSON 文本字段）
     */
    public static PoolOperationVO toVO(PoolOperationPO po, ObjectMapper mapper) {
        if (po == null) return null;
        PoolOperationVO vo = new PoolOperationVO();
        vo.setId(po.getId());
        vo.setPoolId(po.getPoolId());
        vo.setOperationType(po.getOperationType());
        vo.setStatus(po.getStatus());
        vo.setParams(parseJsonObject(po.getParams(), mapper));
        vo.setResultSummary(parseJsonAny(po.getResultSummary(), mapper));
        vo.setProgress(toProgress(po.getProgress(), mapper));
        vo.setErrorMessage(po.getErrorMessage());
        vo.setStartedAt(po.getStartedAt());
        vo.setFinishedAt(po.getFinishedAt());
        vo.setCreatedAt(po.getCreatedAt());
        return vo;
    }

    public static List<PoolOperationVO> toOperationVOList(List<PoolOperationPO> pos, ObjectMapper mapper) {
        return pos == null ? List.of() : pos.stream().map(po -> toVO(po, mapper)).toList();
    }

    /** 从 JSON 文本解析进度 */
    public static OperationProgressVO toProgress(String progressJson, ObjectMapper mapper) {
        Map<String, Object> raw = parseJsonObject(progressJson, mapper);
        OperationProgressVO vo = new OperationProgressVO();
        vo.setDone(intOf(raw.get("done")));
        vo.setTotal(intOf(raw.get("total")));
        vo.setFailed(intOf(raw.get("failed")));
        return vo;
    }

    private static int intOf(Object value) {
        return value instanceof Number number ? number.intValue() : 0;
    }

    private static Map<String, Object> parseJsonObject(String json, ObjectMapper mapper) {
        if (json == null || json.isBlank()) return Map.of();
        try {
            return mapper.readValue(json, new TypeReference<Map<String, Object>>() {});
        } catch (Exception e) {
            return Map.of();
        }
    }

    private static Object parseJsonAny(String json, ObjectMapper mapper) {
        if (json == null || json.isBlank()) return null;
        try {
            return mapper.readValue(json, Object.class);
        } catch (Exception e) {
            return json;
        }
    }
}
