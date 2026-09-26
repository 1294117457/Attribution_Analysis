package com.attribution.domain.repository;

import com.attribution.domain.entity.FinTop10HolderEntity;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.stereotype.Repository;

import java.time.LocalDate;
import java.util.List;

@Repository
public interface FinTop10HolderRepository extends JpaRepository<FinTop10HolderEntity, Long> {

    List<FinTop10HolderEntity> findBySymbolAndEndDate(String symbol, LocalDate endDate);

    List<FinTop10HolderEntity> findBySymbolOrderByEndDateDesc(String symbol);
}
