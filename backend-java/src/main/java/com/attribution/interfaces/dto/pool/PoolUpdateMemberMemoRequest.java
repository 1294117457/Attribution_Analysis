package com.attribution.interfaces.dto.pool;

import lombok.AllArgsConstructor;
import lombok.Builder;
import lombok.Data;
import lombok.NoArgsConstructor;

@Data
@Builder
@NoArgsConstructor
@AllArgsConstructor
public class PoolUpdateMemberMemoRequest {

    private String symbol;
    private String memo;
}
