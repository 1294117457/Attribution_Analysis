package com.attribution.interfaces.dto.pool;

import jakarta.validation.constraints.NotEmpty;
import lombok.AllArgsConstructor;
import lombok.Builder;
import lombok.Data;
import lombok.NoArgsConstructor;

import java.util.List;

@Data
@Builder
@NoArgsConstructor
@AllArgsConstructor
public class PoolRemoveMembersRequest {

    @NotEmpty
    private List<String> symbols;
}
