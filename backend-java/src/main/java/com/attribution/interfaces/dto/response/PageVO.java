package com.attribution.interfaces.dto.response;

import io.swagger.v3.oas.annotations.media.Schema;
import lombok.AllArgsConstructor;
import lombok.Builder;
import lombok.Data;
import lombok.NoArgsConstructor;

import java.util.Collections;
import java.util.List;

/**
 * 统一分页响应结构
 *
 * <p>对应设计文档 docs/design/api/02-page-vo.md §2.1
 *
 * <pre>
 * {
 *   "total": 153,
 *   "page": 1,
 *   "pageSize": 20,
 *   "dataList": [ ... ]
 * }
 * </pre>
 *
 * @param <T> 数据项类型
 */
@Data
@Builder
@NoArgsConstructor
@AllArgsConstructor
@Schema(description = "统一分页响应结构")
public class PageVO<T> {

    @Schema(description = "总记录数（≥ dataList.length）")
    private long total;

    @Schema(description = "当前页号（从 1 开始）")
    private int page;

    @Schema(description = "页大小")
    private int pageSize;

    @Schema(description = "当前页数据列表（空列表返回 []，永不返回 null）")
    private List<T> dataList;

    /**
     * 创建空分页结果（查不到数据时使用）。
     */
    public static <T> PageVO<T> empty(int page, int pageSize) {
        PageVO<T> vo = new PageVO<>();
        vo.total = 0L;
        vo.page = page;
        vo.pageSize = pageSize;
        vo.dataList = Collections.emptyList();
        return vo;
    }

    /**
     * 构造分页结果。
     *
     * @param total    总记录数
     * @param page     当前页
     * @param pageSize 页大小
     * @param dataList 数据列表（为 null 时自动转为空列表）
     */
    public static <T> PageVO<T> of(long total, int page, int pageSize, List<T> dataList) {
        PageVO<T> vo = new PageVO<>();
        vo.total = total;
        vo.page = page;
        vo.pageSize = pageSize;
        vo.dataList = dataList == null ? Collections.emptyList() : dataList;
        return vo;
    }
}
