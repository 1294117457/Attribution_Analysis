package com.attribution.interfaces.dto.operation;

import lombok.AllArgsConstructor;
import lombok.Builder;
import lombok.Data;
import lombok.NoArgsConstructor;

@Data
@Builder
@NoArgsConstructor
@AllArgsConstructor
public class PoolOperationProgressVO {

    private Integer done;
    private Integer total;
    private Integer failed;
}
