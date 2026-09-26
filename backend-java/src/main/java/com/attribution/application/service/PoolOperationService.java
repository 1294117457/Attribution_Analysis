package com.attribution.application.service;

import com.attribution.domain.entity.PoolOperationEntity;
import com.attribution.domain.entity.StockPoolEntity;
import com.attribution.interfaces.dto.operation.PoolKlineCollectRequest;
import com.attribution.interfaces.dto.operation.PoolOperationCreateVO;
import com.attribution.interfaces.dto.operation.PoolOperationListRequest;
import com.attribution.interfaces.dto.operation.PoolOperationListVO;
import com.attribution.interfaces.dto.operation.PoolOperationProgressVO;
import com.attribution.interfaces.dto.operation.PoolOperationVO;
import com.attribution.infrastructure.exception.BusinessException;
import org.springframework.http.HttpStatus;
import com.attribution.domain.repository.PoolOperationRepository;
import com.attribution.domain.repository.StockPoolMemberRepository;
import com.attribution.domain.repository.StockPoolRepository;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import java.util.HashMap;
import java.util.List;
import java.util.Map;

@Service
@RequiredArgsConstructor
@Slf4j
public class PoolOperationService {

    private final StockPoolRepository poolRepository;
    private final StockPoolMemberRepository memberRepository;
    private final PoolOperationRepository operationRepository;
    private final OperationDispatcher operationDispatcher;

    @Transactional
    public PoolOperationCreateVO createKlineCollectOperation(PoolKlineCollectRequest request) {
        StockPoolEntity pool = poolRepository.findById(request.getPoolId())
            .orElseThrow(() -> new BusinessException("pool", "POOL_NOT_FOUND", "操作池不存在: " + request.getPoolId(), HttpStatus.NOT_FOUND));

        List<PoolOperationEntity> existing = operationRepository.findByStatusIn(List.of("pending", "running"));
        boolean conflict = existing.stream()
            .anyMatch(op -> op.getPoolId() != null && op.getPoolId().equals(request.getPoolId()));
        if (conflict) {
            throw new BusinessException("operation", "OPERATION_CONFLICT", "_" + request.getPoolId() + " 存在未完成的操作", HttpStatus.CONFLICT);
        }

        List<String> symbols = memberRepository.findByPoolIdOrderBySortOrderAsc(request.getPoolId())
            .stream()
            .map(m -> m.getSymbol())
            .toList();

        if (symbols.isEmpty()) {
            return PoolOperationCreateVO.builder()
                .operationId(0L)
                .poolId(request.getPoolId())
                .operationType(request.getOperationType())
                .status("skipped")
                .total(0)
                .message("池内没有成员")
                .build();
        }

        Map<String, Object> params = new HashMap<>();
        params.put("days", request.getDays());

        PoolOperationEntity entity = PoolOperationEntity.builder()
            .poolId(request.getPoolId())
            .operationType(request.getOperationType())
            .status("pending")
            .params(params)
            .progress(Map.of("done", 0, "total", symbols.size(), "failed", 0))
            .build();
        PoolOperationEntity saved = operationRepository.save(entity);

        operationDispatcher.dispatchKlineCollect(saved.getId(), request.getPoolId(), symbols, request.getDays());

        return PoolOperationCreateVO.builder()
            .operationId(saved.getId())
            .poolId(request.getPoolId())
            .operationType(request.getOperationType())
            .status("pending")
            .total(symbols.size())
            .message("操作已派发，_" + symbols.size() + " 只股")
            .build();
    }

    @Transactional(readOnly = true)
    public PoolOperationListVO listOperations(PoolOperationListRequest request) {
        if (!poolRepository.existsById(request.getPoolId())) {
            throw new BusinessException("pool", "POOL_NOT_FOUND", "操作池不存在: " + request.getPoolId(), HttpStatus.NOT_FOUND);
        }
        List<PoolOperationEntity> ops = operationRepository.findByPoolIdOrderByCreatedAtDesc(request.getPoolId());
        List<PoolOperationVO> items = ops.stream()
            .skip(request.getOffset() != null ? request.getOffset() : 0)
            .limit(request.getLimit() != null ? request.getLimit() : ops.size())
            .map(PoolOperationVO::fromEntity)
            .toList();
        return PoolOperationListVO.builder()
            .poolId(request.getPoolId())
            .total(items.size())
            .dataList(items)
            .build();
    }

    @Transactional(readOnly = true)
    public PoolOperationVO getOperation(Long opId) {
        PoolOperationEntity entity = operationRepository.findById(opId)
            .orElseThrow(() -> new BusinessException("operation", "OPERATION_NOT_FOUND", "操作不存_ " + opId, HttpStatus.NOT_FOUND));
        return PoolOperationVO.fromEntity(entity);
    }

    @Transactional(readOnly = true)
    public PoolOperationProgressVO getOperationProgress(Long opId) {
        PoolOperationEntity entity = operationRepository.findById(opId)
            .orElseThrow(() -> new BusinessException("operation", "OPERATION_NOT_FOUND", "操作不存_ " + opId, HttpStatus.NOT_FOUND));
        return PoolOperationVO.fromEntity(entity).getProgress();
    }

    @Transactional
    public PoolOperationVO cancelOperation(Long opId) {
        PoolOperationEntity entity = operationRepository.findById(opId)
            .orElseThrow(() -> new BusinessException("operation", "OPERATION_NOT_FOUND", "操作不存_ " + opId, HttpStatus.NOT_FOUND));
        if (!List.of("pending", "running").contains(entity.getStatus())) {
            throw new BusinessException("operation", "CANNOT_CANCEL", "该操作无法取", HttpStatus.BAD_REQUEST);
        }
        operationDispatcher.cancel(opId);
        entity.setStatus("cancelled");
        PoolOperationEntity saved = operationRepository.save(entity);
        return PoolOperationVO.fromEntity(saved);
    }
}
