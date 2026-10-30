package com.attribution.collector.client;

import java.util.Map;

import lombok.Data;

@Data
public class CollectRequest {
    private String mode = "condition";
    private Map<String, Object> params;
}
