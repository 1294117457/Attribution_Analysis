package com.attribution.concept.controller;

import java.util.ArrayList;
import java.util.Arrays;
import java.util.List;

import org.springframework.web.bind.annotation.*;

import com.attribution.common.response.ApiResponse;
import com.attribution.concept.service.ConceptService;

import lombok.RequiredArgsConstructor;

@RestController
@RequestMapping("/api/concepts")
@RequiredArgsConstructor
public class ConceptQuoteController {
    private final ConceptService conceptService;

    @GetMapping("/quotes")
    public ApiResponse<?> quotes(@RequestParam String codes) {
        List<String> indexCodes = new ArrayList<>(Arrays.asList(codes.split(",")));
        if (indexCodes.size() > 100) return ApiResponse.fail(400, "codes 最多 100 个");
        return ApiResponse.ok(conceptService.quotes(indexCodes));
    }

    @GetMapping("/{index_code}/minute")
    public ApiResponse<?> minute(@PathVariable String indexCode) {
        return ApiResponse.ok(conceptService.minute(indexCode));
    }
}
