package com.attribution.domain.repository;

import com.attribution.domain.entity.CapMarginDetailEntity;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.stereotype.Repository;

import java.time.LocalDate;
import java.util.List;
import java.util.Optional;

@Repository
public interface CapMarginDetailRepository extends JpaRepository<CapMarginDetailEntity, Long> {

    Optional<CapMarginDetailEntity> findBySymbolAndTradeDate(String symbol, LocalDate tradeDate);

    List<CapMarginDetailEntity> findBySymbolAndTradeDateBetweenOrderByTradeDateDesc(
        String symbol, LocalDate start, LocalDate end);
}
