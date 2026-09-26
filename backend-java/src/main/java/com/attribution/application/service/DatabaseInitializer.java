package com.attribution.application.service;

import com.attribution.domain.entity.StockPoolEntity;
import com.attribution.domain.repository.StockPoolRepository;
import jakarta.annotation.PostConstruct;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

@Service
@RequiredArgsConstructor
@Slf4j
public class DatabaseInitializer {

    private final StockPoolRepository poolRepository;

    @PostConstruct
    @Transactional
    public void init() {
        ensureDefaultPool();
    }

    @Transactional
    public void ensureDefaultPool() {
        if (poolRepository.findFirstByIsDefaultTrue().isPresent()) {
            return;
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
        poolRepository.save(defaultPool);
        log.info("已创建默认池：我的自");
    }
}
