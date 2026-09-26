package com.attribution.domain.repository;

import com.attribution.domain.entity.CapMoneyflowEntity;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.data.jpa.repository.Query;
import org.springframework.data.repository.query.Param;
import org.springframework.stereotype.Repository;

import java.time.LocalDate;
import java.util.List;
import java.util.Optional;

@Repository
public interface CapMoneyflowRepository extends JpaRepository<CapMoneyflowEntity, Long> {

    Optional<CapMoneyflowEntity> findBySymbolAndTradeDate(String symbol, LocalDate tradeDate);

    List<CapMoneyflowEntity> findBySymbolAndTradeDateBetweenOrderByTradeDateDesc(
        String symbol, LocalDate start, LocalDate end);

    List<CapMoneyflowEntity> findByTradeDate(LocalDate tradeDate);

    @Query("SELECT m FROM CapMoneyflowEntity m WHERE m.tradeDate = :date AND m.symbol IN :symbols")
    List<CapMoneyflowEntity> findByTradeDateAndSymbolIn(
        @Param("date") LocalDate date, @Param("symbols") List<String> symbols);
}
