package com.attribution.domain.repository;

import com.attribution.domain.entity.StockPoolEntity;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.data.jpa.repository.Query;
import org.springframework.data.repository.query.Param;
import org.springframework.stereotype.Repository;

import java.util.List;
import java.util.Optional;

@Repository
public interface StockPoolRepository extends JpaRepository<StockPoolEntity, Long> {

    List<StockPoolEntity> findByPoolType(String poolType);

    List<StockPoolEntity> findByNameContaining(String keyword);

    List<StockPoolEntity> findByIsArchivedOrderBySortOrderAsc(boolean isArchived);

    @Query("SELECT p FROM StockPoolEntity p WHERE p.isDefault = true ORDER BY p.id ASC")
    Optional<StockPoolEntity> findFirstByIsDefaultTrue();
}
