package com.attribution.application.service;

import com.attribution.interfaces.dto.pool.PoolAddMembersRequest;
import com.attribution.interfaces.dto.pool.PoolAddMembersVO;
import com.attribution.interfaces.dto.pool.PoolCreateRequest;
import com.attribution.interfaces.dto.pool.PoolDetailVO;
import com.attribution.interfaces.dto.pool.PoolListVO;
import com.attribution.interfaces.dto.pool.PoolMemberListVO;
import com.attribution.interfaces.dto.pool.PoolMemberVO;
import com.attribution.interfaces.dto.pool.PoolPoolsBySymbolVO;
import com.attribution.interfaces.dto.pool.PoolRemoveMembersRequest;
import com.attribution.interfaces.dto.pool.PoolUpdateMemberMemoRequest;
import com.attribution.interfaces.dto.pool.PoolUpdateRequest;
import com.attribution.interfaces.dto.pool.PoolVO;
import com.attribution.domain.entity.StockPoolEntity;
import com.attribution.domain.entity.StockPoolMemberEntity;
import com.attribution.domain.entity.StockInfoEntity;
import com.attribution.infrastructure.exception.BusinessException;
import org.springframework.http.HttpStatus;
import com.attribution.domain.repository.StockInfoRepository;
import com.attribution.domain.repository.StockPoolMemberRepository;
import com.attribution.domain.repository.StockPoolRepository;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import java.util.ArrayList;
import java.util.List;
import java.util.Map;

@Service
@RequiredArgsConstructor
@Slf4j
public class StockPoolService {

    private final StockPoolRepository poolRepository;
    private final StockPoolMemberRepository memberRepository;
    private final StockInfoRepository stockRepository;

    @Transactional
    public PoolVO createPool(PoolCreateRequest request) {
        StockPoolEntity entity = StockPoolEntity.builder()
            .name(request.getName().trim())
            .poolType(request.getPoolType() != null ? request.getPoolType() : "custom")
            .description(request.getDescription())
            .color(request.getColor())
            .icon(request.getIcon())
            .sortOrder(0)
            .isDefault(Boolean.TRUE.equals(request.getIsDefault()))
            .isArchived(false)
            .build();
        StockPoolEntity saved = poolRepository.save(entity);
        return PoolVO.fromEntity(saved, 0);
    }

    @Transactional(readOnly = true)
    public PoolListVO listPools(boolean includeArchived, int limit, int offset) {
        List<StockPoolEntity> pools;
        if (includeArchived) {
            pools = poolRepository.findAll().stream()
                .sorted((a, b) -> Integer.compare(
                    a.getSortOrder() != null ? a.getSortOrder() : 0,
                    b.getSortOrder() != null ? b.getSortOrder() : 0))
                .toList();
        } else {
            pools = poolRepository.findByIsArchivedOrderBySortOrderAsc(false);
        }
        List<PoolVO> items = pools.stream()
            .skip(offset)
            .limit(limit)
            .map(p -> PoolVO.fromEntity(p, (int) memberRepository.countByPoolId(p.getId())))
            .toList();
        return PoolListVO.builder()
            .total(items.size())
            .dataList(items)
            .build();
    }

    @Transactional(readOnly = true)
    public PoolDetailVO getPool(Long poolId) {
        StockPoolEntity entity = poolRepository.findById(poolId)
            .orElseThrow(() -> new BusinessException("pool", "POOL_NOT_FOUND", "操作池不存在: " + poolId, HttpStatus.NOT_FOUND));
        PoolVO poolVO = PoolVO.fromEntity(entity, (int) memberRepository.countByPoolId(poolId));
        List<StockPoolMemberEntity> members = memberRepository.findByPoolIdOrderBySortOrderAsc(poolId);
        List<PoolMemberVO> memberVOs = members.stream()
            .map(this::toMemberVO)
            .toList();
        return PoolDetailVO.from(poolVO, memberVOs);
    }

    @Transactional
    public PoolVO updatePool(Long poolId, PoolUpdateRequest request) {
        StockPoolEntity entity = poolRepository.findById(poolId)
            .orElseThrow(() -> new BusinessException("pool", "POOL_NOT_FOUND", "操作池不存在: " + poolId, HttpStatus.NOT_FOUND));
        if (request.getName() != null && !request.getName().isBlank()) {
            entity.setName(request.getName().trim());
        }
        if (request.getDescription() != null) {
            entity.setDescription(request.getDescription());
        }
        if (request.getColor() != null) {
            entity.setColor(request.getColor());
        }
        if (request.getIcon() != null) {
            entity.setIcon(request.getIcon());
        }
        if (request.getSortOrder() != null) {
            entity.setSortOrder(request.getSortOrder());
        }
        StockPoolEntity saved = poolRepository.save(entity);
        return PoolVO.fromEntity(saved, (int) memberRepository.countByPoolId(poolId));
    }

    @Transactional
    public void deletePool(Long poolId) {
        StockPoolEntity entity = poolRepository.findById(poolId)
            .orElseThrow(() -> new BusinessException("pool", "POOL_NOT_FOUND", "操作池不存在: " + poolId, HttpStatus.NOT_FOUND));
        if (Boolean.TRUE.equals(entity.getIsDefault())) {
            throw new BusinessException("pool", "CANNOT_DELETE_DEFAULT_POOL", "无法删除默认_ " + poolId, HttpStatus.BAD_REQUEST);
        }
        poolRepository.delete(entity);
    }

    @Transactional
    public PoolAddMembersVO addMembers(Long poolId, PoolAddMembersRequest request) {
        if (!poolRepository.existsById(poolId)) {
            throw new BusinessException("pool", "POOL_NOT_FOUND", "操作池不存在: " + poolId, HttpStatus.NOT_FOUND);
        }

        List<String> validSymbols = new ArrayList<>();
        List<String> skipped = new ArrayList<>();

        if (Boolean.TRUE.equals(request.getValidateExists())) {
            for (String symbol : request.getSymbols()) {
                if (stockRepository.findBySymbol(symbol).isPresent()) {
                    validSymbols.add(symbol);
                } else {
                    skipped.add(symbol);
                }
            }
        } else {
            validSymbols = new ArrayList<>(request.getSymbols());
        }

        List<String> added = new ArrayList<>();
        int nextSortOrder = (int) memberRepository.countByPoolId(poolId);

        for (String symbol : validSymbols) {
            if (memberRepository.findOneByPoolIdAndSymbol(poolId, symbol).isPresent()) {
                skipped.add(symbol);
                continue;
            }
            StockPoolMemberEntity member = StockPoolMemberEntity.builder()
                .poolId(poolId)
                .symbol(symbol)
                .memo("")
                .sortOrder(nextSortOrder++)
                .build();
            memberRepository.save(member);
            added.add(symbol);
        }

        return PoolAddMembersVO.builder()
            .poolId(poolId)
            .added(added)
            .skipped(skipped)
            .totalAdded(added.size())
            .totalSkipped(skipped.size())
            .build();
    }

    @Transactional
    public int removeMembers(Long poolId, PoolRemoveMembersRequest request) {
        if (!poolRepository.existsById(poolId)) {
            throw new BusinessException("pool", "POOL_NOT_FOUND", "操作池不存在: " + poolId, HttpStatus.NOT_FOUND);
        }
        return memberRepository.deleteByPoolIdAndSymbolIn(poolId, request.getSymbols());
    }

    @Transactional(readOnly = true)
    public PoolMemberListVO listMembers(Long poolId, int limit, int offset) {
        if (!poolRepository.existsById(poolId)) {
            throw new BusinessException("pool", "POOL_NOT_FOUND", "操作池不存在: " + poolId, HttpStatus.NOT_FOUND);
        }
        List<StockPoolMemberEntity> members = memberRepository.findByPoolIdOrderBySortOrderAsc(poolId);
        List<PoolMemberVO> items = members.stream()
            .skip(offset)
            .limit(limit)
            .map(this::toMemberVO)
            .toList();
        return PoolMemberListVO.builder()
            .poolId(poolId)
            .total((int) memberRepository.countByPoolId(poolId))
            .dataList(items)
            .build();
    }

    @Transactional
    public PoolMemberVO updateMemberMemo(Long poolId, PoolUpdateMemberMemoRequest request) {
        if (!poolRepository.existsById(poolId)) {
            throw new BusinessException("pool", "POOL_NOT_FOUND", "操作池不存在: " + poolId, HttpStatus.NOT_FOUND);
        }
        StockPoolMemberEntity member = memberRepository.findOneByPoolIdAndSymbol(poolId, request.getSymbol())
            .orElseThrow(() -> new BusinessException("pool", "MEMBER_NOT_FOUND", "股票 " + request.getSymbol() + " 不在_" + poolId + " ", HttpStatus.NOT_FOUND));
        member.setMemo(request.getMemo());
        memberRepository.save(member);

        PoolMemberVO vo = PoolMemberVO.fromEntity(member);
        StockInfoEntity stock = stockRepository.findBySymbol(member.getSymbol()).orElse(null);
        if (stock != null) {
            vo.setName(stock.getName());
            vo.setIndustry(stock.getIndustry());
            vo.setMarket(stock.getMarket());
            vo.setExchange(stock.getExchange());
        }
        return vo;
    }

    @Transactional(readOnly = true)
    public PoolPoolsBySymbolVO findPoolsBySymbol(String symbol) {
        List<Object[]> rows = memberRepository.findPoolsBySymbol(symbol);
        List<PoolVO> poolVOs = new ArrayList<>();
        for (Object[] row : rows) {
            Long pid = (Long) row[0];
            String name = (String) row[1];
            StockPoolEntity pool = poolRepository.findById(pid).orElse(null);
            if (pool != null) {
                poolVOs.add(PoolVO.fromEntity(pool, (int) memberRepository.countByPoolId(pid)));
            }
        }
        return PoolPoolsBySymbolVO.builder()
            .symbol(symbol)
            .pools(poolVOs)
            .total(poolVOs.size())
            .build();
    }

    @Transactional
    public PoolVO ensureDefaultPool() {
        var existing = poolRepository.findFirstByIsDefaultTrue();
        if (existing.isPresent()) {
            var e = existing.get();
            return PoolVO.fromEntity(e, (int) memberRepository.countByPoolId(e.getId()));
        }
        StockPoolEntity defaultPool = StockPoolEntity.builder()
            .name("我的自")
            .poolType("watchlist")
            .isDefault(true)
            .isArchived(false)
            .sortOrder(0)
            .icon("")
            .color("#FFB800")
            .build();
        StockPoolEntity saved = poolRepository.save(defaultPool);
        return PoolVO.fromEntity(saved, 0);
    }

    private PoolMemberVO toMemberVO(StockPoolMemberEntity e) {
        PoolMemberVO vo = PoolMemberVO.fromEntity(e);
        StockInfoEntity stock = stockRepository.findBySymbol(e.getSymbol()).orElse(null);
        if (stock != null) {
            vo.setName(stock.getName());
            vo.setIndustry(stock.getIndustry());
            vo.setMarket(stock.getMarket());
            vo.setExchange(stock.getExchange());
            vo.setIsValid(true);
        } else {
            vo.setIsValid(false);
        }
        return vo;
    }

    private void copyPoolFields(PoolVO vo, StockPoolEntity e, int memberCount) {
        vo.setId(e.getId());
        vo.setName(e.getName());
        vo.setPoolType(e.getPoolType());
        vo.setDescription(e.getDescription());
        vo.setColor(e.getColor());
        vo.setIcon(e.getIcon());
        vo.setSortOrder(e.getSortOrder());
        vo.setIsDefault(e.getIsDefault());
        vo.setIsArchived(e.getIsArchived());
        vo.setMemberCount(memberCount);
        vo.setCreatedAt(e.getCreatedAt());
        vo.setUpdatedAt(e.getUpdatedAt());
    }
}
