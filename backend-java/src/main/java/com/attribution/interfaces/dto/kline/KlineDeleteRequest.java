package com.attribution.interfaces.dto.kline;

import jakarta.validation.constraints.Min;
import jakarta.validation.constraints.NotBlank;
import lombok.AllArgsConstructor;
import lombok.Builder;
import lombok.Data;
import lombok.NoArgsConstructor;

import java.time.LocalDate;

@Data
@Builder
@NoArgsConstructor
@AllArgsConstructor
public class KlineDeleteRequest {

    @NotBlank
    private String symbol;

    private LocalDate tradeDate;
}
