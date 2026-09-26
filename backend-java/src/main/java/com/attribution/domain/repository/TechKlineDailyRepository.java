package com.attribution.domain.repository;

import com.attribution.domain.entity.TechKlineDailyEntity;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.data.jpa.repository.Query;
import org.springframework.data.repository.query.Param;
import org.springframework.stereotype.Repository;

import java.time.LocalDate;
import java.util.List;
import java.util.Optional;

@Repository
public interface TechKlineDailyRepository extends JpaRepository<TechKlineDailyEntity, Long> {

    List<TechKlineDailyEntity> findBySymbolOrderByDateDesc(String symbol);

    List<TechKlineDailyEntity> findBySymbolOrderByDateAsc(String symbol);

    List<TechKlineDailyEntity> findBySymbolAndDateBetweenOrderByDateAsc(
        String symbol, LocalDate startDate, LocalDate endDate);

    List<TechKlineDailyEntity> findBySymbolAndDateBetweenOrderByDateDesc(
        String symbol, LocalDate startDate, LocalDate endDate);

    Optional<TechKlineDailyEntity> findFirstBySymbolOrderByDateDesc(String symbol);

    Optional<TechKlineDailyEntity> findBySymbolAndDate(String symbol, LocalDate date);

    long countBySymbol(String symbol);

    @Query("SELECT MIN(k.date), MAX(k.date), COUNT(k) FROM TechKlineDailyEntity k WHERE k.symbol = :symbol")
    Object[] aggregateStats(@Param("symbol") String symbol);

    @Query("SELECT k.symbol, MIN(k.date), MAX(k.date), COUNT(k) " +
           "FROM TechKlineDailyEntity k WHERE k.symbol IN :symbols GROUP BY k.symbol")
    List<Object[]> aggregateStatsBySymbols(@Param("symbols") List<String> symbols);

    void deleteBySymbol(String symbol);

    void deleteBySymbolAndDate(String symbol, LocalDate date);

    List<TechKlineDailyEntity> findByDate(LocalDate date);

    @Query("SELECT k FROM TechKlineDailyEntity k WHERE k.date = :date AND k.symbol IN :symbols")
    List<TechKlineDailyEntity> findByDateAndSymbolIn(
        @Param("date") LocalDate date, @Param("symbols") List<String> symbols);

    @Query("SELECT MAX(k.date) FROM TechKlineDailyEntity k")
    Optional<LocalDate> findLastTradeDate();

    @Query("SELECT k FROM TechKlineDailyEntity k WHERE k.symbol IN :symbols "
        + "AND k.date BETWEEN :start AND :end ORDER BY k.symbol, k.date ASC")
    List<TechKlineDailyEntity> findBySymbolsAndDateRange(
        @Param("symbols") List<String> symbols,
        @Param("start") LocalDate start,
        @Param("end") LocalDate end);
}
