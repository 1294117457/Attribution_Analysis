package com.attribution.domain.repository;

import com.attribution.domain.entity.CapTopInstEntity;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.stereotype.Repository;

import java.time.LocalDate;
import java.util.List;

@Repository
public interface CapTopInstRepository extends JpaRepository<CapTopInstEntity, Long> {

    List<CapTopInstEntity> findByTradeDate(LocalDate tradeDate);

    List<CapTopInstEntity> findBySymbolAndTradeDate(String symbol, LocalDate tradeDate);
}
