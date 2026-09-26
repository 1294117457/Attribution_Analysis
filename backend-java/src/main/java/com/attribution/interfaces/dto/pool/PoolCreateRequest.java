package com.attribution.interfaces.dto.pool;

import jakarta.validation.constraints.NotBlank;
import lombok.AllArgsConstructor;
import lombok.Builder;
import lombok.Data;
import lombok.NoArgsConstructor;

@Data
@Builder
@NoArgsConstructor
@AllArgsConstructor
public class PoolCreateRequest {

    @NotBlank
    private String name;

    @Builder.Default
    private String poolType = "custom";

    private String description;
    private String color;
    private String icon;

    @Builder.Default
    private Boolean isDefault = false;
}
