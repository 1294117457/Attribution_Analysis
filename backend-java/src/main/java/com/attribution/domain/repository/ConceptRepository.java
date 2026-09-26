package com.attribution.domain.repository;

import com.attribution.domain.entity.ConceptEntity;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.data.jpa.repository.Query;
import org.springframework.data.repository.query.Param;
import org.springframework.stereotype.Repository;

import java.util.Collection;
import java.util.List;

@Repository
public interface ConceptRepository extends JpaRepository<ConceptEntity, Long> {

    List<ConceptEntity> findBySource(String source);

    @Query("SELECT c FROM ConceptEntity c WHERE c.id IN :ids")
    List<ConceptEntity> findByIdIn(@Param("ids") Collection<Long> ids);

    @Query("SELECT c FROM ConceptEntity c WHERE c.name LIKE %:keyword%")
    List<ConceptEntity> searchByName(@Param("keyword") String keyword);

    @Query("SELECT c FROM ConceptEntity c WHERE c.isActive = true")
    List<ConceptEntity> findAllActive();
}
