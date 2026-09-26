package com.attribution.interfaces.dto;

import lombok.AllArgsConstructor;
import lombok.Builder;
import lombok.Data;
import lombok.NoArgsConstructor;

import java.time.LocalDate;

@Data
@Builder
@NoArgsConstructor
@AllArgsConstructor
public class TopHolderVO {

    private String holderName;
    private String holderType;
    private Double holdAmount;
    private Double holdRatio;
    private Double holdFloatRatio;
    private Double holdChange;
    private LocalDate endDate;
}
