package com.attribution.market.service;

import com.attribution.common.response.PageResult;
import com.attribution.market.dto.CollectLogQuery;
import com.attribution.market.vo.CollectLogVO;

/** 采集历史：查 PG collect_logs（collector 写、Java 只读），与 Redis 进度无关。 */
public interface CollectLogService {
    PageResult<CollectLogVO> page(CollectLogQuery query);
}
