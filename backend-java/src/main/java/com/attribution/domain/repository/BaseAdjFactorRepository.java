package com.attribution.domain.repository;

import com.attribution.domain.entity.BaseAdjFactorEntity;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.stereotype.Repository;

import java.time.LocalDate;
import java.util.List;
import java.util.Optional;

@Repository
public interface BaseAdjFactorRepository extends JpaRepository<BaseAdjFactorEntity, Long> {

    Optional<BaseAdjFactorEntity> findBySymbolAndTradeDate(String symbol, LocalDate tradeDate);

    List<BaseAdjFactorEntity> findBySymbolAndTradeDateBetweenOrderByTradeDateAsc(
        String symbol, LocalDate start, LocalDate end);
}
