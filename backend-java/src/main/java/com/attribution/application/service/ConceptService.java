package com.attribution.application.service;

import com.attribution.domain.entity.ConceptEntity;
import com.attribution.domain.entity.ConceptMemberEntity;
import com.attribution.domain.entity.SysCollectTaskEntity;
import com.attribution.domain.repository.ConceptMemberRepository;
import com.attribution.domain.repository.ConceptRepository;
import com.attribution.domain.repository.SysCollectTaskRepository;
import com.attribution.infrastructure.exception.BusinessException;
import com.attribution.interfaces.dto.ConceptBriefVO;
import com.attribution.interfaces.dto.ConceptDetailVO;
import com.attribution.interfaces.dto.ConceptMemberVO;
import com.attribution.interfaces.dto.ConceptSyncStatusVO;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import java.time.OffsetDateTime;
import java.util.Collections;
import java.util.List;
import java.util.Map;
import java.util.function.Function;
import java.util.stream.Collectors;

@Slf4j
@Service
@RequiredArgsConstructor
public class ConceptService {

    private final ConceptRepository conceptRepository;
    private final ConceptMemberRepository conceptMemberRepository;
    private final SysCollectTaskRepository taskRepository;

    public List<ConceptBriefVO> getAllConcepts(String source) {
        List<ConceptEntity> concepts = source != null
            ? conceptRepository.findBySource(source)
            : conceptRepository.findAll();
        return concepts.stream().map(this::toBrief).toList();
    }

    public ConceptDetailVO getConceptDetail(String code) {
        Long conceptId;
        try {
            conceptId = Long.parseLong(code);
        } catch (NumberFormatException e) {
            throw new BusinessException("concept", "CONCEPT_NOT_FOUND",
                    "概念不存在: " + code, 404);
        }
        ConceptEntity concept = conceptRepository.findById(conceptId)
            .orElseThrow(() -> new BusinessException("concept", "CONCEPT_NOT_FOUND",
                    "概念不存在: " + code, 404));

        List<ConceptMemberEntity> members = conceptMemberRepository.findByConceptId(concept.getId());
        return ConceptDetailVO.builder()
            .code(concept.getCode())
            .name(concept.getName())
            .source(concept.getSource())
            .memberCount(members.size())
            .members(members.stream()
                .map(this::toMember)
                .toList())
            .recentDailies(Collections.emptyList())
            .build();
    }

    public List<ConceptBriefVO> getStockConcepts(String symbol) {
        List<ConceptMemberEntity> members = conceptMemberRepository.findBySymbol(symbol);
        if (members.isEmpty()) {
            return Collections.emptyList();
        }
        List<Long> conceptIds = members.stream().map(ConceptMemberEntity::getConceptId).toList();
        Map<Long, ConceptEntity> conceptMap = conceptRepository.findAllById(conceptIds).stream()
            .collect(Collectors.toMap(ConceptEntity::getId, Function.identity()));
        return members.stream()
            .filter(m -> conceptMap.containsKey(m.getConceptId()))
            .map(m -> toBrief(conceptMap.get(m.getConceptId())))
            .toList();
    }

    public ConceptSyncStatusVO getSyncStatus(String source) {
        List<SysCollectTaskEntity> tasks = taskRepository.findByTaskTypeOrderByStartedAtDesc("concept_" + source);
        if (tasks == null || tasks.isEmpty()) {
            return ConceptSyncStatusVO.builder()
                .source(source)
                .hasHistory(false)
                .build();
        }
        SysCollectTaskEntity last = tasks.get(0);
        return ConceptSyncStatusVO.builder()
            .source(source)
            .hasHistory(true)
            .lastTaskId(last.getId())
            .lastStatus(last.getStatus())
            .lastMessage(last.getMessage())
            .lastStartedAt(last.getStartedAt() != null ? last.getStartedAt().toString() : null)
            .lastFinishedAt(last.getFinishedAt() != null ? last.getFinishedAt().toString() : null)
            .lastTotal(last.getTotalCount())
            .lastSuccess(last.getSuccessCount())
            .lastFail(last.getFailCount())
            .build();
    }

    @Transactional
    public ConceptEntity saveConcept(String name, String source) {
        // 通过 (name, source) 找现有，没有就新建
        return conceptRepository.findAll().stream()
            .filter(c -> name.equals(c.getName()) && source.equals(c.getSource()))
            .findFirst()
            .map(c -> {
                c.setName(name);
                c.setLastSyncedAt(OffsetDateTime.now());
                return conceptRepository.save(c);
            })
            .orElseGet(() -> conceptRepository.save(
                ConceptEntity.builder()
                    .name(name)
                    .source(source)
                    .conceptType("other")
                    .stockCount(0)
                    .isActive(true)
                    .firstSeenAt(OffsetDateTime.now())
                    .build()));
    }

    @Transactional
    public void saveMember(Long conceptId, String symbol, String name) {
        boolean exists = conceptMemberRepository.findByConceptId(conceptId).stream()
            .anyMatch(m -> symbol.equals(m.getSymbol()));
        if (exists) {
            return;
        }
        ConceptMemberEntity member = ConceptMemberEntity.builder()
            .conceptId(conceptId)
            .symbol(symbol)
            .name(name)
            .build();
        conceptMemberRepository.save(member);
    }

    // ── VO 转换 ─────────────────────────────────────────────
    private ConceptBriefVO toBrief(ConceptEntity c) {
        return ConceptBriefVO.builder()
            .code(c.getCode())
            .conceptId(c.getCode())
            .name(c.getName())
            .source(c.getSource())
            .build();
    }

    private ConceptMemberVO toMember(ConceptMemberEntity m) {
        return ConceptMemberVO.builder()
            .symbol(m.getSymbol())
            .name(m.getName())
            .effectiveDate(m.getEffectiveDate())
            .expiryDate(m.getExpiryDate())
            .isNew(m.getIsNew())
            .build();
    }
}
