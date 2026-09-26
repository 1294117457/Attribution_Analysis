package com.attribution.application.service;

import com.attribution.interfaces.dto.StockPanelQuery;
import com.attribution.interfaces.dto.StockPanelResponse;
import com.attribution.interfaces.dto.StockPanelRowVO;
import com.attribution.domain.repository.StockPanelComposeRepository;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.stereotype.Service;

import java.util.List;

@Slf4j
@Service
@RequiredArgsConstructor
public class StockPanelService {

    private final StockPanelComposeRepository composeRepository;

    public StockPanelResponse queryPanel(StockPanelQuery query) {
        List<StockPanelRowVO> rows = composeRepository.queryPanel(query);
        long total = composeRepository.countPanel(query);
        return StockPanelResponse.builder()
            .rows(rows)
            .total(total)
            .page(query.getPage())
            .size(query.getSize())
            .tradeDate(query.getTradeDate())
            .build();
    }
}
