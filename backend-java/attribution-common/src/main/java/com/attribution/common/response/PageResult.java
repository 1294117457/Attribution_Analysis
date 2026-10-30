package com.attribution.common.response;

import java.util.List;

import lombok.Data;

@Data
public class PageResult<T> {
    private long total;
    private List<T> list;
    private int page;
    private int pageSize;

    public static <T> PageResult<T> of(long total, List<T> list, int page, int pageSize) {
        PageResult<T> result = new PageResult<>();
        result.total = total;
        result.list = list;
        result.page = page;
        result.pageSize = pageSize;
        return result;
    }
}
