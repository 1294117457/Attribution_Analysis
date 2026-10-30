package com.attribution.market.controller;

import org.springframework.web.bind.annotation.*;

import com.attribution.common.response.ApiResponse;
import com.attribution.common.response.PageResult;
import com.attribution.market.dto.CollectLogQuery;
import com.attribution.market.service.CollectLogService;
import com.attribution.market.vo.CollectLogVO;

import jakarta.validation.Valid;
import lombok.RequiredArgsConstructor;

/**
 * 采集历史：查 PG collect_logs（collector 写、Java 只读），不经过 Redis。
 *
 * <p>规范见 {@code docs/开发文档/采集模块/采集模块现状文档（三类采集：增量-全量覆盖-实时查询）.md} §4.2。
 */
@RestController
@RequestMapping("/api/collect/logs")
@RequiredArgsConstructor
public class CollectLogController {
    private final CollectLogService collectLogService;

    @GetMapping
    public ApiResponse<PageResult<CollectLogVO>> page(
            @Valid @ModelAttribute CollectLogQuery query) {
        return ApiResponse.ok(collectLogService.page(query));
    }
}
