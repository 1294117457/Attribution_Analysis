package com.attribution.domain.repository;

import com.attribution.domain.entity.PoolOperationEntity;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.stereotype.Repository;

import java.util.List;

@Repository
public interface PoolOperationRepository extends JpaRepository<PoolOperationEntity, Long> {

    List<PoolOperationEntity> findByPoolIdOrderByCreatedAtDesc(Long poolId);

    List<PoolOperationEntity> findByStatusIn(List<String> statuses);
}
