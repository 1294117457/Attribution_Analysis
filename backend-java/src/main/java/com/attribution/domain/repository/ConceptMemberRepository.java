package com.attribution.domain.repository;

import com.attribution.domain.entity.ConceptMemberEntity;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.data.jpa.repository.Query;
import org.springframework.data.repository.query.Param;
import org.springframework.stereotype.Repository;

import java.time.LocalDate;
import java.util.List;

@Repository
public interface ConceptMemberRepository extends JpaRepository<ConceptMemberEntity, Long> {

    List<ConceptMemberEntity> findByConceptId(Long conceptId);

    List<ConceptMemberEntity> findBySymbol(String symbol);

    @Query("""
        SELECT m FROM ConceptMemberEntity m
        WHERE m.symbol IN :symbols
        AND (m.expiryDate IS NULL OR m.expiryDate >= :asOf)
        """)
    List<ConceptMemberEntity> findActiveBySymbolIn(
        @Param("symbols") List<String> symbols,
        @Param("asOf") LocalDate asOf);

    @Query("SELECT m FROM ConceptMemberEntity m WHERE m.symbol IN :symbols")
    List<ConceptMemberEntity> findBySymbolIn(@Param("symbols") List<String> symbols);
}
