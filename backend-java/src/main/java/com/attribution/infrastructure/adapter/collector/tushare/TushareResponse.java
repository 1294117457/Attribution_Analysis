package com.attribution.infrastructure.adapter.collector.tushare;

import com.fasterxml.jackson.annotation.JsonIgnoreProperties;
import com.fasterxml.jackson.annotation.JsonProperty;
import lombok.Data;

import java.util.List;

@Data
@JsonIgnoreProperties(ignoreUnknown = true)
public class TushareResponse {

    @JsonProperty("code")
    private int code;

    @JsonProperty("msg")
    private String msg;

    @JsonProperty("data")
    private TushareData data;

    @Data
    @JsonIgnoreProperties(ignoreUnknown = true)
    public static class TushareData {
        @JsonProperty("fields")
        private List<String> fields;

        @JsonProperty("items")
        private List<List<Object>> items;

        @JsonProperty("has_more")
        private Boolean hasMore;

        @JsonProperty("count")
        private Integer count;
    }
}
