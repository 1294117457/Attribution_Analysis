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
public class ConceptMemberVO {

    private String symbol;
    private String name;
    private LocalDate effectiveDate;
    private LocalDate expiryDate;
    private String isNew;
}
