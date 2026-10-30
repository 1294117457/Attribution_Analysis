package com.attribution.concept.service;

import java.util.List;
import java.util.Map;

import com.attribution.common.response.PageResult;
import com.attribution.concept.dto.ConceptBoardQuery;
import com.attribution.concept.dto.ConceptKlineQuery;
import com.attribution.concept.dto.ConceptMemberQuery;
import com.attribution.concept.dto.ConceptQuery;
import com.attribution.concept.vo.ConceptBriefVO;
import com.attribution.concept.vo.ConceptBoardItemVO;
import com.attribution.concept.vo.ConceptDetailVO;
import com.attribution.concept.vo.ConceptKlineBarVO;
import com.attribution.concept.vo.ConceptKlineResponseVO;
import com.attribution.concept.vo.ConceptLiveVO;
import com.attribution.concept.vo.ConceptMemberItemVO;
import com.attribution.concept.vo.ConceptMinuteVO;
import com.attribution.concept.vo.ConceptSnapshotVO;
import com.attribution.concept.vo.ConceptSyncStatusVO;
import com.attribution.concept.vo.ConceptTabContentVO;
import com.attribution.concept.vo.ConceptVO;

/**
 * 概念服务。
 *
 * <p>接口签名统一使用 DTO（入参）与 VO（出参），不暴露 PO 与裸 Map。
 */
public interface ConceptService {
    PageResult<ConceptVO> list(ConceptQuery query);

    List<ConceptBriefVO> bySymbol(String symbol);

    List<ConceptLiveVO> liveBySymbol(String symbol);

    ConceptTabContentVO tab(String symbol, String stockName, boolean mergeLive);

    ConceptSyncStatusVO syncStatus();

    ConceptDetailVO detail(String conceptName);

    List<ConceptKlineBarVO> indexKline(
            String conceptName, String startDate, String endDate, int limit);

    PageResult<ConceptBoardItemVO> board(ConceptBoardQuery query);

    PageResult<ConceptMemberItemVO> members(ConceptMemberQuery query);

    ConceptKlineResponseVO conceptKline(String indexCode, ConceptKlineQuery query);

    /**
     * 批量概念实时行情。
     *
     * <p>返回 Map 的 key 为 index_code —— 这是前端契约（{@code Record<string, ConceptSnapshot>}），
     * 动态键无法用 POJO 表达，故保留 Map 结构，但 value 使用强类型 VO。
     */
    Map<String, ConceptSnapshotVO> quotes(List<String> codes);

    ConceptMinuteVO minute(String indexCode);
}
