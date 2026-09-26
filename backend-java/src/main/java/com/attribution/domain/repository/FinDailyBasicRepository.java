package com.attribution.domain.repository;

import com.attribution.domain.entity.FinDailyBasicEntity;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.data.jpa.repository.Query;
import org.springframework.data.repository.query.Param;
import org.springframework.stereotype.Repository;

import java.time.LocalDate;
import java.util.List;
import java.util.Optional;

@Repository
public interface FinDailyBasicRepository extends JpaRepository<FinDailyBasicEntity, Long> {

    Optional<FinDailyBasicEntity> findBySymbolAndTradeDate(String symbol, LocalDate tradeDate);

    List<FinDailyBasicEntity> findBySymbolAndTradeDateBetweenOrderByTradeDateDesc(
        String symbol, LocalDate start, LocalDate end);

    List<FinDailyBasicEntity> findByTradeDate(LocalDate tradeDate);

    @Query("SELECT b FROM FinDailyBasicEntity b WHERE b.tradeDate = :date AND b.symbol IN :symbols")
    List<FinDailyBasicEntity> findByTradeDateAndSymbolIn(
        @Param("date") LocalDate date, @Param("symbols") List<String> symbols);

    /** 全市场最新估值交易日（由用户参数覆盖时优先使用） */
    @Query("SELECT MAX(b.tradeDate) FROM FinDailyBasicEntity b")
    Optional<LocalDate> findLastTradeDate();
}
