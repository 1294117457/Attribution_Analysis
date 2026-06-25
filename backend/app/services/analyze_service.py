"""分析服务"""

from typing import List, Optional
from datetime import date
import statistics

from sqlalchemy.orm import Session

from app.models.kline import KLine
from app.models.report import Report
from app.schemas.analyze import AnalyzeResponse, AnomalyResult


class AnalyzeService:
    """分析服务 - 异常检测与归因分析"""

    def __init__(self, db: Session):
        self.db = db

    async def detect_anomaly(
        self, symbol: str, start_date: date, end_date: date
    ) -> tuple[bool, List[AnomalyResult]]:
        """
        异常检测

        Args:
            symbol: 股票代码
            start_date: 开始日期
            end_date: 结束日期

        Returns:
            (是否有异常, 异常列表)
        """
        # 获取K线数据
        klines = (
            self.db.query(KLine)
            .filter(
                KLine.code == symbol,
                KLine.date >= start_date,
                KLine.date <= end_date,
            )
            .order_by(KLine.date)
            .all()
        )

        if not klines:
            return False, []

        anomalies: List[AnomalyResult] = []

        # 提取价格列表
        prices = [k.close for k in klines]
        changes = [k.change_pct for k in klines if k.change_pct is not None]

        # === 异常检测算法 ===

        # 1. 涨跌幅异常检测（超过 5%）
        for kline in klines:
            if kline.change_pct is not None:
                if abs(kline.change_pct) > 10:
                    severity = "high"
                elif abs(kline.change_pct) > 5:
                    severity = "medium"
                elif abs(kline.change_pct) > 3:
                    severity = "low"
                else:
                    continue

                anomalies.append(
                    AnomalyResult(
                        type="price_change",
                        severity=severity,
                        value=kline.change_pct,
                        description=f"涨跌幅异常: {kline.change_pct:+.2f}%",
                        date=str(kline.date),
                    )
                )

        # 2. 波动率异常检测
        if len(prices) >= 20:
            recent_prices = prices[-20:]
            mean_price = statistics.mean(recent_prices)
            stdev_price = statistics.stdev(recent_prices)

            # 当前价格偏离均值超过 2 个标准差
            if recent_prices[-1] > mean_price + 2 * stdev_price:
                anomalies.append(
                    AnomalyResult(
                        type="high_price",
                        severity="medium",
                        value=recent_prices[-1],
                        description=f"价格异常偏高: {recent_prices[-1]:.2f} (均值: {mean_price:.2f})",
                        date=str(klines[-1].date),
                    )
                )
            elif recent_prices[-1] < mean_price - 2 * stdev_price:
                anomalies.append(
                    AnomalyResult(
                        type="low_price",
                        severity="medium",
                        value=recent_prices[-1],
                        description=f"价格异常偏低: {recent_prices[-1]:.2f} (均值: {mean_price:.2f})",
                        date=str(klines[-1].date),
                    )
                )

        # 3. 成交量异常检测（超过均量 3 倍）
        if len(klines) >= 10:
            avg_volume = statistics.mean([k.volume for k in klines[-10:]])
            current_volume = klines[-1].volume
            if current_volume > avg_volume * 3:
                anomalies.append(
                    AnomalyResult(
                        type="volume_surge",
                        severity="medium",
                        value=current_volume / avg_volume,
                        description=f"成交量异常放大: {current_volume:.0f} (均量: {avg_volume:.0f})",
                        date=str(klines[-1].date),
                    )
                )

        return len(anomalies) > 0, anomalies

    async def generate_report(
        self,
        symbol: str,
        start_date: date,
        end_date: date,
        anomalies: List[AnomalyResult],
    ) -> str:
        """生成分析报告（简化版，后续接入 LLM）"""
        # 获取股票信息
        klines = (
            self.db.query(KLine)
            .filter(
                KLine.code == symbol,
                KLine.date >= start_date,
                KLine.date <= end_date,
            )
            .order_by(KLine.date)
            .all()
        )

        if not klines:
            return f"# 分析报告\n\n股票 {symbol} 在此期间无数据"

        name = klines[0].name if klines else symbol
        first_close = klines[0].close
        last_close = klines[-1].close
        total_change = ((last_close - first_close) / first_close * 100) if first_close else 0

        report = f"""# 归因分析报告

## 基本信息

- **股票代码**: {symbol}
- **股票名称**: {name}
- **分析区间**: {start_date} 至 {end_date}
- **数据天数**: {len(klines)} 天

## 行情摘要

| 指标 | 数值 |
|------|------|
| 区间涨跌幅 | {total_change:+.2f}% |
| 区间最高价 | {max(k.close for k in klines):.2f} |
| 区间最低价 | {min(k.close for k in klines):.2f} |
| 区间成交量 | {sum(k.volume for k in klines):,.0f} 手 |

## 异常检测结果

"""

        if anomalies:
            report += f"检测到 **{len(anomalies)}** 项异常：\n\n"
            for a in anomalies:
                report += f"- [{a.severity.upper()}] {a.description}"
                if a.date:
                    report += f" ({a.date})"
                report += "\n"
        else:
            report += "未检测到明显异常\n"

        report += "\n## 结论\n\n"
        if anomalies:
            high_severity = [a for a in anomalies if a.severity == "high"]
            if high_severity:
                report += f"发现 {len(high_severity)} 项高风险异常，建议重点关注。\n"
            else:
                report += "发现部分异常，但整体风险可控。\n"
        else:
            report += "区间内无明显异常，行情走势平稳。\n"

        return report

    async def analyze(
        self, symbol: str, start_date: date, end_date: date
    ) -> AnalyzeResponse:
        """完整分析流程"""
        # 1. 异常检测
        is_anomaly, anomalies = await self.detect_anomaly(symbol, start_date, end_date)

        # 2. 生成报告
        report = await self.generate_report(symbol, start_date, end_date, anomalies)

        # 3. 计算置信度（简化版）
        confidence = 0.8 if anomalies else 0.9

        return AnalyzeResponse(
            symbol=symbol,
            start_date=str(start_date),
            end_date=str(end_date),
            is_anomaly=is_anomaly,
            anomalies=anomalies,
            report=report,
            confidence=confidence,
        )
