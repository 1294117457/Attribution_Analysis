package com.attribution.market.service.impl;

import java.time.LocalDateTime;
import java.time.OffsetDateTime;
import java.time.ZoneOffset;

import org.springframework.stereotype.Service;

import com.attribution.common.response.PageResult;
import com.attribution.market.converter.CollectLogConverter;
import com.attribution.market.dto.CollectLogQuery;
import com.attribution.market.entity.CollectLogPO;
import com.attribution.market.mapper.CollectLogMapper;
import com.attribution.market.service.CollectLogService;
import com.attribution.market.vo.CollectLogVO;
import com.baomidou.mybatisplus.core.conditions.query.LambdaQueryWrapper;
import com.baomidou.mybatisplus.extension.plugins.pagination.Page;

import lombok.RequiredArgsConstructor;

@Service
@RequiredArgsConstructor
public class CollectLogServiceImpl implements CollectLogService {

    /**
     * 日期筛选用的时区。
     *
     * <p>⚠️ {@code collect_logs.created_at} 是 {@code timestamptz}，
     * 筛选时必须带时区 —— 否则「某一天」的边界会偏 8 小时。
     * 与远端 PG 的 {@code SET timezone = 'Asia/Shanghai'} 保持一致。
     *
     * <p>中国无夏令时 → 固定 +08:00 偏移即可，不必用 {@code ZonedDateTime}
     * （PG 驱动无法推断 {@code ZonedDateTime} 的 SQL 类型 → 报
     * "Can't infer the SQL type to use for an instance of java.time.ZonedDateTime"）。
     */
    private static final ZoneOffset ZONE = ZoneOffset.ofHours(8);

    private final CollectLogMapper collectLogMapper;

    /** LocalDateTime → 带偏移的 OffsetDateTime（+08:00）。 */
    private static OffsetDateTime _offset(LocalDateTime t) {
        return t.atOffset(ZONE);
    }

    @Override
    public PageResult<CollectLogVO> page(CollectLogQuery query) {
        LambdaQueryWrapper<CollectLogPO> wrapper = new LambdaQueryWrapper<>();
        if (isNotBlank(query.getFacet()))
            wrapper.eq(CollectLogPO::getFacet, query.getFacet().trim());
        if (isNotBlank(query.getName()))
            wrapper.eq(CollectLogPO::getName, query.getName().trim());
        if (isNotBlank(query.getStatus()))
            wrapper.eq(CollectLogPO::getStatus, query.getStatus().trim());
        if (isNotBlank(query.getTriggerSource()))
            wrapper.eq(CollectLogPO::getTriggerSource, query.getTriggerSource().trim());
        // ★ 按采集方式筛选（kind 列承载 strategy：incremental / full）
        if (isNotBlank(query.getKind()))
            wrapper.eq(CollectLogPO::getKind, query.getKind().trim());
        if (query.getStartDate() != null)
            wrapper.ge(CollectLogPO::getCreatedAt, _offset(query.getStartDate().atStartOfDay()));
        if (query.getEndDate() != null)
            wrapper.le(CollectLogPO::getCreatedAt, _offset(query.getEndDate().atTime(23, 59, 59)));
        if (Boolean.TRUE.equals(query.getHasFail()))
            wrapper.gt(CollectLogPO::getFail, 0);

        // ★ 先 count（不带 orderBy）
        //   orderByDesc 后再 selectCount(wrapper) 会生成
        //   SELECT count(*) ... ORDER BY collect_logs.created_at DESC
        //   在 PG 下报 "column collect_logs.id must appear in the GROUP BY clause"。
        //   本项目已犯过这个错。
        long total = collectLogMapper.selectCount(wrapper);

        // ★ 再排序分页（必须带稳定排序键，否则翻页结果不稳定）
        wrapper.orderByDesc(CollectLogPO::getCreatedAt).orderByDesc(CollectLogPO::getTaskId);
        Page<CollectLogPO> page = collectLogMapper.selectPage(
                new Page<>(query.getPage(), query.getPageSize()), wrapper);
        return CollectLogConverter.toPageResult(
                total, page.getRecords(), query.getPage(), query.getPageSize());
    }

    private static boolean isNotBlank(String s) {
        return s != null && !s.isBlank();
    }
}
