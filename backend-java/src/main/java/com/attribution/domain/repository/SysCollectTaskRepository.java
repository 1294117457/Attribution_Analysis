package com.attribution.domain.repository;

import com.attribution.domain.entity.SysCollectTaskEntity;
import org.springframework.data.domain.Page;
import org.springframework.data.domain.Pageable;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.stereotype.Repository;

import java.util.List;

@Repository
public interface SysCollectTaskRepository extends JpaRepository<SysCollectTaskEntity, Long> {

    List<SysCollectTaskEntity> findByTaskTypeOrderByStartedAtDesc(String taskType);

    List<SysCollectTaskEntity> findTop20ByOrderByStartedAtDesc();

    Page<SysCollectTaskEntity> findByTaskTypeAndStatusOrderByIdDesc(String taskType, String status, Pageable pageable);

    Page<SysCollectTaskEntity> findByTaskTypeOrderByIdDesc(String taskType, Pageable pageable);

    Page<SysCollectTaskEntity> findByStatusOrderByIdDesc(String status, Pageable pageable);

    Page<SysCollectTaskEntity> findAllByOrderByIdDesc(Pageable pageable);
}
