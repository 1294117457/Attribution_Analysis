package com.attribution.domain.repository;

import com.attribution.domain.entity.FinReportEntity;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.data.jpa.repository.Query;
import org.springframework.data.repository.query.Param;
import org.springframework.stereotype.Repository;

import java.time.LocalDate;
import java.util.List;
import java.util.Optional;

@Repository
public interface FinReportRepository extends JpaRepository<FinReportEntity, Long> {

    Optional<FinReportEntity> findBySymbolAndEndDate(String symbol, LocalDate endDate);

    List<FinReportEntity> findBySymbolOrderByEndDateDesc(String symbol);

    /**
     * 取某只股票「最新一期」财报（end_date 最大的一行）。
     * <p>
     * 用于面板/详情页直接派生净利润率%、同比等派生指标：
     * 调用方拿到这条 entity 后交给 {@code ProfitabilityDomainService} 计算。
     */
    Optional<FinReportEntity> findFirstBySymbolOrderByEndDateDesc(String symbol);

    /**
     * 批量取 page 内所有 symbol 的全部财报行，由调用方在内存里按 symbol 选最大 end_date，
     * 避免 N+1（每只股票一条 sql）。
     */
    @Query("SELECT f FROM FinReportEntity f WHERE f.symbol IN :symbols")
    List<FinReportEntity> findAllBySymbols(@Param("symbols") List<String> symbols);

    @Query("SELECT f FROM FinReportEntity f WHERE f.symbol = :symbol "
        + "AND f.endDate <= :endDate ORDER BY f.endDate DESC")
    List<FinReportEntity> findRecent(@Param("symbol") String symbol, @Param("endDate") LocalDate endDate);
}
