package com.attribution.interfaces.dto.stock;

import com.attribution.interfaces.dto.kline.KlineVO;
import lombok.EqualsAndHashCode;

@EqualsAndHashCode(callSuper = true)
public class KlineWithIndicatorVO extends KlineVO {

    public KlineWithIndicatorVO() {
        super();
    }

    public static KlineWithIndicatorVO fromKlineVO(KlineVO k) {
        KlineWithIndicatorVO vo = new KlineWithIndicatorVO();
        vo.setDate(k.getDate());
        vo.setSymbol(k.getSymbol());
        vo.setName(k.getName());
        vo.setOpen(k.getOpen());
        vo.setHigh(k.getHigh());
        vo.setLow(k.getLow());
        vo.setClose(k.getClose());
        vo.setVolume(k.getVolume());
        vo.setAmount(k.getAmount());
        vo.setChangePct(k.getChangePct());
        vo.setMa5(k.getMa5());
        vo.setMa10(k.getMa10());
        vo.setMa20(k.getMa20());
        vo.setMa60(k.getMa60());
        vo.setEma12(k.getEma12());
        vo.setEma26(k.getEma26());
        vo.setMacdDif(k.getMacdDif());
        vo.setMacdDea(k.getMacdDea());
        vo.setMacdBar(k.getMacdBar());
        vo.setRsi6(k.getRsi6());
        vo.setRsi12(k.getRsi12());
        vo.setRsi24(k.getRsi24());
        vo.setKdjK(k.getKdjK());
        vo.setKdjD(k.getKdjD());
        vo.setKdjJ(k.getKdjJ());
        vo.setBollUp(k.getBollUp());
        vo.setBollMid(k.getBollMid());
        vo.setBollDn(k.getBollDn());
        return vo;
    }
}
