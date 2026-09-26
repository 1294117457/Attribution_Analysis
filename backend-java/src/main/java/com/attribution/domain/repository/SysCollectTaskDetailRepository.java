package com.attribution.domain.repository;

import com.attribution.domain.entity.SysCollectTaskDetailEntity;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.stereotype.Repository;

import java.util.List;

@Repository
public interface SysCollectTaskDetailRepository extends JpaRepository<SysCollectTaskDetailEntity, Long> {

    List<SysCollectTaskDetailEntity> findByTaskId(Long taskId);
}
