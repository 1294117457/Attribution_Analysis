package com.attribution.domain.repository;

import com.attribution.interfaces.dto.StockPanelQuery;
import com.attribution.interfaces.dto.StockPanelRowVO;

import java.util.List;

public interface StockPanelComposeRepository {

    List<StockPanelRowVO> queryPanel(StockPanelQuery query);

    long countPanel(StockPanelQuery query);
}
