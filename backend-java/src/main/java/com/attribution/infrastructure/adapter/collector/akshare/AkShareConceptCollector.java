package com.attribution.infrastructure.adapter.collector.akshare;

import com.attribution.domain.entity.ConceptEntity;
import com.attribution.domain.entity.ConceptMemberEntity;
import com.attribution.domain.repository.ConceptMemberRepository;
import com.attribution.domain.repository.ConceptRepository;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.stereotype.Component;
import org.springframework.web.reactive.function.client.WebClient;
import reactor.core.publisher.Mono;

import java.time.Duration;
import java.util.*;

/**
 * AKShare 概念板块采集器（Java 端等价实现）_ *
 * 说明：原_akshare _Python 库。本实现直接通过 HTTP 调用东方财富
 * 公开接口（push2.eastmoney.com），无需 Python 依赖，行为与 Python _ * <code>ak.stock_board_concept_name_em()</code> / <code>ak.stock_board_concept_cons_em()</code> 一致_ *
 * 接口列表_ *   - 概念清单：https://push2.eastmoney.com/api/qt/clist/get?pn=1&pz=200&fs=m:90+t:2&fields=f1,f2,f3,f12,f13,f14
 *   - 成分股：  https://push2.eastmoney.com/api/qt/clist/get?pn=1&pz=200&fs=m:90+t:2+f:!{code}&fields=f12,f14
 */
@Slf4j
@Component
@RequiredArgsConstructor
public class AkShareConceptCollector {

    private final ConceptRepository conceptRepository;
    private final ConceptMemberRepository conceptMemberRepository;

    @Value("${attribution.akshare.base-url:https://push2.eastmoney.com}")
    private String baseUrl;

    @Value("${attribution.akshare.timeout-ms:8000}")
    private int timeoutMs;

    private final WebClient webClient = WebClient.builder().build();

    public static final String SOURCE = "akshare";

    /**
     * 拉取全量概念清单 _落库（增_upsert）_     * @return 保存/更新的概念数
     */
    public int fetchConceptList() {
        try {
            Mono<Map> mono = webClient.get()
                .uri(baseUrl + "/api/qt/clist/get"
                    + "?pn=1&pz=500&po=1&np=1&fltt=2&invt=2&fs=m:90+t:2"
                    + "&fields=f1,f2,f3,f12,f13,f14,f3")
                .retrieve()
                .bodyToMono(Map.class)
                .timeout(Duration.ofMillis(timeoutMs));

            @SuppressWarnings("unchecked")
            Map<String, Object> resp = mono.block();
            if (resp == null) return 0;

            Object dataObj = resp.get("data");
            if (!(dataObj instanceof Map<?, ?> data)) return 0;
            Object diffObj = data.get("diff");
            if (!(diffObj instanceof List<?> diff)) return 0;

            int saved = 0;
            for (Object item : diff) {
                if (!(item instanceof Map<?, ?> m)) continue;
                String code = str(m.get("f12"));
                String name = str(m.get("f14"));
                if (code == null || code.isBlank() || name == null || name.isBlank()) continue;

                // 用 (name, source) 查现有；没有则新建。DB 没有 concept_code 列。
                ConceptEntity concept = conceptRepository.findAll().stream()
                    .filter(c -> name.equals(c.getName()) && SOURCE.equals(c.getSource()))
                    .findFirst()
                    .orElseGet(() -> ConceptEntity.builder()
                        .name(name)
                        .source(SOURCE)
                        .conceptType("other")
                        .stockCount(0)
                        .isActive(true)
                        .firstSeenAt(java.time.OffsetDateTime.now())
                        .build());
                concept.setLastSyncedAt(java.time.OffsetDateTime.now());
                conceptRepository.save(concept);
                saved++;
            }
            log.info("AKShare 概念清单同步: {} ", saved);
            return saved;
        } catch (Exception e) {
            log.error("AKShare fetchConceptList 失败: {}", e.getMessage());
            return 0;
        }
    }

    /**
     * 拉取指定概念的成分股 _落库_
     * @param conceptName 概念名称（兼容老 Python collector 签名）
     * @return 新增成员_
     */
    public int fetchConceptStocks(String conceptCode, String conceptName) {
        // 兼容老调用：用概念名称 + source 找到 concept_id
        ConceptEntity concept = conceptRepository.findAll().stream()
            .filter(c -> conceptName != null && conceptName.equals(c.getName()) && SOURCE.equals(c.getSource()))
            .findFirst()
            .orElseGet(() -> conceptRepository.save(ConceptEntity.builder()
                .name(conceptName != null ? conceptName : conceptCode)
                .source(SOURCE)
                .conceptType("other")
                .stockCount(0)
                .isActive(true)
                .firstSeenAt(java.time.OffsetDateTime.now())
                .build()));
        Long conceptId = concept.getId();

        try {
            // 兼容：原 conceptCode（东方财富 BK0xxx）仍用于 URL 拉取成分股
            String urlCode = conceptCode != null ? conceptCode : conceptName;
            Mono<Map> mono = webClient.get()
                .uri(baseUrl + "/api/qt/clist/get"
                    + "?pn=1&pz=500&po=1&np=1&fltt=2&invt=2&fs=m:90+t:2+f:!" + urlCode
                    + "&fields=f12,f14,f2,f3")
                .retrieve()
                .bodyToMono(Map.class)
                .timeout(Duration.ofMillis(timeoutMs));

            @SuppressWarnings("unchecked")
            Map<String, Object> resp = mono.block();
            if (resp == null) return 0;
            Object dataObj = resp.get("data");
            if (!(dataObj instanceof Map<?, ?> data)) return 0;
            Object diffObj = data.get("diff");
            if (!(diffObj instanceof List<?> diff)) return 0;

            // 取已存在成员去重
            Set<String> existingSymbols = new HashSet<>();
            conceptMemberRepository.findByConceptId(conceptId)
                .forEach(m -> existingSymbols.add(m.getSymbol()));

            int added = 0;
            for (Object item : diff) {
                if (!(item instanceof Map<?, ?> m)) continue;
                String symbol = padSymbol(str(m.get("f12")));
                String name = str(m.get("f14"));
                if (symbol == null || symbol.length() != 6) continue;
                if (existingSymbols.contains(symbol)) continue;

                ConceptMemberEntity member = ConceptMemberEntity.builder()
                    .conceptId(conceptId)
                    .symbol(symbol)
                    .name(name != null ? name : symbol)
                    .isNew("Y")
                    .build();
                conceptMemberRepository.save(member);
                added++;
            }
            log.info("AKShare 概念 [{}] 成分股同_ 新增 {} ", conceptName, added);
            return added;
        } catch (Exception e) {
            log.warn("AKShare fetchConceptStocks 失败: code={}, {}", conceptCode, e.getMessage());
            return 0;
        }
    }

    private static String str(Object v) {
        return v == null ? null : v.toString().trim();
    }

    private static String padSymbol(String s) {
        if (s == null) return null;
        // 去除交易所前缀（如 "1." 或 "0."）
        int dot = s.indexOf('.');
        if (dot >= 0 && dot + 1 < s.length()) {
            s = s.substring(dot + 1);
        }
        if (s.length() >= 6) return s.substring(s.length() - 6);
        return String.format("%6s", s).replace(' ', '0');
    }
}
