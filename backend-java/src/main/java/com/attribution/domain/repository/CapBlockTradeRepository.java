package com.attribution.domain.repository;

import com.attribution.domain.entity.CapBlockTradeEntity;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.stereotype.Repository;

import java.time.LocalDate;
import java.util.List;

@Repository
public interface CapBlockTradeRepository extends JpaRepository<CapBlockTradeEntity, Long> {

    List<CapBlockTradeEntity> findByTradeDate(LocalDate tradeDate);

    List<CapBlockTradeEntity> findBySymbolAndTradeDateBetweenOrderByTradeDateDesc(
        String symbol, LocalDate start, LocalDate end);
}
