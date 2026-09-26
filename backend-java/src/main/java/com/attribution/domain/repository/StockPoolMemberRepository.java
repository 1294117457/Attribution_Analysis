package com.attribution.domain.repository;

import com.attribution.domain.entity.StockPoolMemberEntity;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.data.jpa.repository.Query;
import org.springframework.data.repository.query.Param;
import org.springframework.stereotype.Repository;

import java.util.List;
import java.util.Optional;

@Repository
public interface StockPoolMemberRepository extends JpaRepository<StockPoolMemberEntity, Long> {

    List<StockPoolMemberEntity> findByPoolId(Long poolId);

    List<StockPoolMemberEntity> findBySymbol(String symbol);

    long countByPoolId(Long poolId);

    List<StockPoolMemberEntity> findByPoolIdOrderBySortOrderAsc(Long poolId);

    List<StockPoolMemberEntity> findByPoolIdAndSymbol(Long poolId, String symbol);

    default Optional<StockPoolMemberEntity> findOneByPoolIdAndSymbol(Long poolId, String symbol) {
        return findByPoolIdAndSymbol(poolId, symbol).stream().findFirst();
    }

    int deleteByPoolIdAndSymbolIn(Long poolId, List<String> symbols);

    @Query("SELECT m.poolId FROM StockPoolMemberEntity m WHERE m.symbol = :symbol")
    List<Long> findPoolIdsBySymbol(@Param("symbol") String symbol);

    @Query("SELECT m.symbol, m.poolId, p.name, p.poolType, m.addedAt FROM StockPoolMemberEntity m " +
           "JOIN StockPoolEntity p ON m.poolId = p.id " +
           "WHERE m.symbol IN :symbols")
    List<Object[]> findPoolsBySymbols(@Param("symbols") List<String> symbols);

    @Query("SELECT m.poolId, p.name FROM StockPoolMemberEntity m " +
           "JOIN StockPoolEntity p ON m.poolId = p.id " +
           "WHERE m.symbol = :symbol")
    List<Object[]> findPoolsBySymbol(@Param("symbol") String symbol);
}
