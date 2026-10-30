package com.attribution.market.converter;

import java.time.OffsetDateTime;
import java.util.List;

import com.attribution.common.response.PageResult;
import com.attribution.market.entity.CollectLogPO;
import com.attribution.market.vo.CollectLogVO;

/**
 * 采集日志 PO → VO 转换器。
 *
 * <p>规范见 {@code docs/开发文档/采集模块/采集模块现状文档（三类采集：增量-全量覆盖-实时查询）.md} §4.2。
 */
public final class CollectLogConverter {

    private CollectLogConverter() {
    }

    public static CollectLogVO toVO(CollectLogPO po) {
        if (po == null) return null;
        CollectLogVO vo = new CollectLogVO();
        vo.setTaskId(po.getTaskId());
        vo.setFacet(po.getFacet());
        vo.setName(po.getName());
        vo.setKind(po.getKind());
        vo.setMode(po.getMode());
        vo.setTriggerSource(po.getTriggerSource());
        vo.setTriggerUser(po.getTriggerUser());
        vo.setParamsJson(po.getParamsJson());
        vo.setRangeStart(po.getRangeStart());
        vo.setRangeEnd(po.getRangeEnd());
        vo.setStatus(po.getStatus());
        vo.setProgress(po.getProgress());
        vo.setTotal(po.getTotal());
        vo.setDone(po.getDone());
        vo.setSuccess(po.getSuccess());
        vo.setFail(po.getFail());
        vo.setSkip(po.getSkip());
        vo.setSavedTotal(po.getSavedTotal());
        vo.setMessage(po.getMessage());
        vo.setError(po.getError());
        vo.setDetail(po.getDetail());
        vo.setCreatedAt(_iso(po.getCreatedAt()));
        vo.setStartedAt(_iso(po.getStartedAt()));
        vo.setFinishedAt(_iso(po.getFinishedAt()));
        vo.setUpdatedAt(_iso(po.getUpdatedAt()));
        vo.setDurationMs(po.getDurationMs());
        vo.setCancelRequested(po.getCancelRequested());
        vo.setCancelledAt(_iso(po.getCancelledAt()));
        vo.setParentTaskId(po.getParentTaskId());
        return vo;
    }

    /** OffsetDateTime → ISO-8601 字符串（null 安全）。 */
    private static String _iso(OffsetDateTime t) {
        return t == null ? null : t.toString();
    }

    public static List<CollectLogVO> toVOList(List<CollectLogPO> pos) {
        return pos == null ? List.of() : pos.stream().map(CollectLogConverter::toVO).toList();
    }

    public static PageResult<CollectLogVO> toPageResult(
            long total, List<CollectLogPO> records, int page, int pageSize) {
        return PageResult.of(total, toVOList(records), page, pageSize);
    }
}
