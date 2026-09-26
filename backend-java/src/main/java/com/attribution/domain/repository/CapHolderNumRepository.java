package com.attribution.domain.repository;

import com.attribution.domain.entity.CapHolderNumEntity;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.stereotype.Repository;

import java.time.LocalDate;
import java.util.List;
import java.util.Optional;

@Repository
public interface CapHolderNumRepository extends JpaRepository<CapHolderNumEntity, Long> {

    Optional<CapHolderNumEntity> findBySymbolAndEndDate(String symbol, LocalDate endDate);

    List<CapHolderNumEntity> findBySymbolOrderByEndDateDesc(String symbol);
}
