package com.attribution.domain.repository;

import com.attribution.domain.entity.FinTop10FloatHolderEntity;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.stereotype.Repository;

import java.time.LocalDate;
import java.util.List;

@Repository
public interface FinTop10FloatHolderRepository extends JpaRepository<FinTop10FloatHolderEntity, Long> {

    List<FinTop10FloatHolderEntity> findBySymbolAndEndDate(String symbol, LocalDate endDate);

    List<FinTop10FloatHolderEntity> findBySymbolOrderByEndDateDesc(String symbol);
}
