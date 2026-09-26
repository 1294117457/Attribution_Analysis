package com.attribution.interfaces.dto.stock;

import lombok.AllArgsConstructor;
import lombok.Builder;
import lombok.Data;
import lombok.NoArgsConstructor;

@Data
@Builder
@NoArgsConstructor
@AllArgsConstructor
public class StockInfoVO {

    private String symbol;
    private String name;
    private String industry;
    private String market;
    private String exchange;
}
