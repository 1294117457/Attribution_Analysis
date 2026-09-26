package com.attribution.domain.repository;

import com.attribution.domain.entity.StockInfoEntity;
import org.springframework.data.domain.Pageable;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.data.jpa.repository.Query;
import org.springframework.data.repository.query.Param;
import org.springframework.stereotype.Repository;

import java.util.List;
import java.util.Optional;

@Repository
public interface StockInfoRepository extends JpaRepository<StockInfoEntity, Long> {

    Optional<StockInfoEntity> findBySymbol(String symbol);

    List<StockInfoEntity> findByIndustry(String industry);

    List<StockInfoEntity> findByMarket(String market);

    org.springframework.data.domain.Page<StockInfoEntity> findByIndustry(String industry, Pageable pageable);

    org.springframework.data.domain.Page<StockInfoEntity> findByMarket(String market, Pageable pageable);

    List<StockInfoEntity> findByExchange(String exchange);

    List<StockInfoEntity> findBySymbolIn(List<String> symbols);

    @Query("""
        SELECT s FROM StockInfoEntity s
        WHERE (:keyword IS NULL OR s.name LIKE %:keyword% OR s.symbol LIKE %:keyword%)
        AND (:industry IS NULL OR s.industry = :industry)
        """)
    List<StockInfoEntity> findPanelPage(
        @Param("keyword") String keyword,
        @Param("industry") String industry,
        Pageable pageable);

    @Query("""
        SELECT COUNT(s) FROM StockInfoEntity s
        WHERE (:keyword IS NULL OR s.name LIKE %:keyword% OR s.symbol LIKE %:keyword%)
        AND (:industry IS NULL OR s.industry = :industry)
        """)
    long countPanel(@Param("keyword") String keyword, @Param("industry") String industry);
}
