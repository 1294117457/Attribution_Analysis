package com.attribution.domain.repository;

import com.attribution.domain.entity.MktMarketDailyEntity;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.stereotype.Repository;

import java.time.LocalDate;
import java.util.List;
import java.util.Optional;

@Repository
public interface MktMarketDailyRepository extends JpaRepository<MktMarketDailyEntity, Long> {

    Optional<MktMarketDailyEntity> findByMarketAndTradeDate(String market, LocalDate tradeDate);

    List<MktMarketDailyEntity> findByMarketAndTradeDateBetweenOrderByTradeDateDesc(
        String market, LocalDate start, LocalDate end);
}
