package com.attribution.domain.repository;

import com.attribution.domain.entity.CapTopListEntity;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.stereotype.Repository;

import java.time.LocalDate;
import java.util.List;

@Repository
public interface CapTopListRepository extends JpaRepository<CapTopListEntity, Long> {

    List<CapTopListEntity> findByTradeDate(LocalDate tradeDate);

    List<CapTopListEntity> findBySymbolAndTradeDateBetweenOrderByTradeDateDesc(
        String symbol, LocalDate start, LocalDate end);
}
