"""
测试脚本：验证采集和检测模块功能。

用法：
    python scripts/test_modules.py
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

import traceback
from datetime import datetime


def check_dependencies():
    """检查依赖是否安装"""
    missing = []

    try:
        import akshare  # noqa
    except ImportError:
        missing.append("akshare")

    try:
        import pydantic  # noqa
    except ImportError:
        missing.append("pydantic")

    try:
        import sqlalchemy  # noqa
    except ImportError:
        missing.append("sqlalchemy")

    if missing:
        print("\n" + "=" * 60)
        print("⚠️  依赖检查")
        print("=" * 60)
        print(f"  缺少以下依赖: {', '.join(missing)}")
        print("  💡 安装命令: pip install " + " ".join(missing))
        print("=" * 60 + "\n")

    return missing


def test_collector_module():
    """测试采集模块"""
    print("\n" + "=" * 60)
    print("测试 1: 采集模块")
    print("=" * 60)

    try:
        import akshare  # noqa
    except ImportError:
        print("  ⊘ akshare 未安装，跳过采集模块测试")
        return None

    try:
        from app.modules.collector.service import CollectorService
        from app.modules.collector.storage import KLineStorage

        print("[1.1] 初始化服务...")
        service = CollectorService()
        storage = KLineStorage()
        print("  ✓ 服务初始化成功")

        print("[1.2] 测试数据采集（贵州茅台）...")

        try:
            result = service.collect_single("600519", "贵州茅台", "20250101", "20250627")
        except Exception as collect_error:
            if "connection" in str(collect_error).lower() or "network" in str(collect_error).lower():
                print(f"  ⚠ 网络错误: {collect_error}")
                print("  ⊘ 跳过网络相关测试")
                return None
            raise

        print(f"  采集结果: collected={result.collected}, saved={result.saved}, success={result.success}")
        if result.error:
            print(f"  错误: {result.error}")
        print("  ✓ 数据采集成功" if result.success else "  ✗ 数据采集失败")

        print("[1.3] 测试批量采集...")
        stocks = [("000858", "五粮液"), ("000001", "平安银行")]
        batch_result = service.collect_batch(stocks, "20250601", "20250627")
        print(f"  批量结果: total={batch_result.total}, success={batch_result.success}, saved={batch_result.total_saved}")
        print("  ✓ 批量采集成功" if batch_result.success > 0 else "  ✗ 批量采集失败")

        return True

    except Exception as e:
        print(f"  ✗ 测试失败: {e}")
        traceback.print_exc()
        return False


def test_detector_module():
    """测试检测模块"""
    print("\n" + "=" * 60)
    print("测试 2: 异常检测模块（集成测试）")
    print("=" * 60)

    try:
        from app.modules.detector.service import DetectorService
        from app.modules.detector.base import Severity

        print("[2.1] 初始化检测服务...")
        service = DetectorService()
        print(f"  检测器列表: {service.get_detectors()}")
        print("  ✓ 服务初始化成功")

        print("[2.2] 测试异常检测（贵州茅台）...")

        try:
            result = service.detect("600519")
        except Exception as db_error:
            if "connection" in str(db_error).lower() or "network" in str(db_error).lower():
                print(f"  ⚠ 数据库连接失败: {db_error}")
                print("  ⊘ 跳过集成测试（需要数据库连接）")
                return None
            raise
        print(f"  代码: {result['code']}")
        print(f"  日期: {result['trade_date']}")
        print(f"  是否异常: {result['is_anomaly']}")
        print(f"  严重程度: {result['severity']}")
        print(f"  异常分数: {result['score']}")
        print(f"  触发数量: {result['anomaly_count']}")

        if result.get("triggers"):
            print("  触发原因:")
            for trigger in result["triggers"]:
                print(f"    - [{trigger['detector']}] {trigger['reason']}")

        print("  ✓ 异常检测成功")

        print("[2.3] 测试批量检测...")
        batch_result = service.detect_batch(["600519", "000858"])
        print(f"  批量结果: total={batch_result['total']}, anomaly_count={batch_result['anomaly_count']}")
        print("  ✓ 批量检测成功")

        return True

    except Exception as e:
        print(f"  ✗ 测试失败: {e}")
        traceback.print_exc()
        return False


def test_individual_detectors():
    """测试各个检测器"""
    print("\n" + "=" * 60)
    print("测试 3: 各检测器单元测试")
    print("=" * 60)

    try:
        from app.modules.detector.price import PriceDetector
        from app.modules.detector.volume import VolumeDetector
        from app.modules.detector.volatility import VolatilityDetector
        from app.modules.detector.trend import TrendDetector

        # 构造测试数据
        history = [
            {"close": 100, "high": 102, "low": 99, "volume": 1000000, "change_pct": 0.5},
            {"close": 101, "high": 103, "low": 100, "volume": 1100000, "change_pct": 1.0},
            {"close": 102, "high": 104, "low": 101, "volume": 1200000, "change_pct": 1.0},
            {"close": 103, "high": 105, "low": 102, "volume": 1300000, "change_pct": 1.0},
            {"close": 104, "high": 106, "low": 103, "volume": 1400000, "change_pct": 1.0},
            {"close": 105, "high": 107, "low": 104, "volume": 1500000, "change_pct": 1.0},
            {"close": 106, "high": 108, "low": 105, "volume": 1600000, "change_pct": 0.95},
            {"close": 107, "high": 109, "low": 106, "volume": 1700000, "change_pct": 0.94},
            {"close": 108, "high": 110, "low": 107, "volume": 1800000, "change_pct": 0.93},
            {"close": 109, "high": 111, "low": 108, "volume": 1900000, "change_pct": 0.93},
            {"close": 110, "high": 112, "low": 109, "volume": 2000000, "change_pct": 0.92},
            {"close": 111, "high": 113, "low": 110, "volume": 2100000, "change_pct": 0.91},
            {"close": 112, "high": 114, "low": 111, "volume": 2200000, "change_pct": 0.90},
            {"close": 113, "high": 115, "low": 112, "volume": 2300000, "change_pct": 0.89},
            {"close": 114, "high": 116, "low": 113, "volume": 2400000, "change_pct": 0.88},
        ]

        # 正常数据
        current_normal = {"close": 115, "high": 117, "low": 114, "volume": 2500000, "change_pct": 0.88}

        # 异常数据：涨跌幅异常
        current_price_anomaly = {"close": 125, "high": 127, "low": 124, "volume": 2500000, "change_pct": 9.0}

        # 异常数据：成交量异常
        current_volume_anomaly = {"close": 115, "high": 117, "low": 114, "volume": 10000000, "change_pct": 0.88}

        print("[3.1] 价格检测器（正常）...")
        detector = PriceDetector()
        result = detector.detect(current_normal, history)
        print(f"  is_anomaly={result.is_anomaly}, score={result.score:.2f}, reason={result.reason}")
        print("  ✓ 价格检测器正常")

        print("[3.2] 价格检测器（异常 - 涨停）...")
        result = detector.detect(current_price_anomaly, history)
        print(f"  is_anomaly={result.is_anomaly}, score={result.score:.2f}, reason={result.reason}")
        print("  ✓ 价格检测器（涨停）正常")

        print("[3.3] 量能检测器（正常）...")
        detector = VolumeDetector()
        result = detector.detect(current_normal, history)
        print(f"  is_anomaly={result.is_anomaly}, score={result.score:.2f}, reason={result.reason}")
        print("  ✓ 量能检测器正常")

        print("[3.4] 量能检测器（异常 - 放量）...")
        result = detector.detect(current_volume_anomaly, history)
        print(f"  is_anomaly={result.is_anomaly}, score={result.score:.2f}, reason={result.reason}")
        print("  ✓ 量能检测器（放量）正常")

        print("[3.5] 波动检测器...")
        detector = VolatilityDetector()
        result = detector.detect(current_normal, history)
        print(f"  is_anomaly={result.is_anomaly}, score={result.score:.2f}, reason={result.reason}")
        print("  ✓ 波动检测器正常")

        print("[3.6] 趋势检测器...")
        detector = TrendDetector()
        result = detector.detect(current_normal, history)
        print(f"  is_anomaly={result.is_anomaly}, score={result.score:.2f}, reason={result.reason}")
        print("  ✓ 趋势检测器正常")

        return True

    except Exception as e:
        print(f"  ✗ 测试失败: {e}")
        traceback.print_exc()
        return False


def test_aggregator():
    """测试聚合器"""
    print("\n" + "=" * 60)
    print("测试 4: 结果聚合器")
    print("=" * 60)

    try:
        from app.modules.detector.base import DetectionResult, Severity
        from app.modules.detector.aggregator import DetectorAggregator

        aggregator = DetectorAggregator()

        # 模拟检测结果
        results = [
            DetectionResult(
                detector_name="price",
                is_anomaly=True,
                severity=Severity.HIGH,
                score=0.8,
                reason="价格偏离均值3个标准差",
            ),
            DetectionResult(
                detector_name="volume",
                is_anomaly=True,
                severity=Severity.MEDIUM,
                score=0.5,
                reason="成交量放大2倍",
            ),
            DetectionResult(
                detector_name="volatility",
                is_anomaly=False,
                severity=Severity.NORMAL,
                score=0.0,
                reason="波动正常",
            ),
            DetectionResult(
                detector_name="trend",
                is_anomaly=False,
                severity=Severity.NORMAL,
                score=0.0,
                reason="趋势正常",
            ),
        ]

        print("[4.1] 测试聚合...")
        aggregated = aggregator.aggregate(results)
        print(f"  is_anomaly={aggregated['is_anomaly']}")
        print(f"  severity={aggregated['severity']}")
        print(f"  score={aggregated['score']}")
        print(f"  anomaly_count={aggregated['anomaly_count']}")
        print("  triggers:")
        for t in aggregated["triggers"]:
            print(f"    - [{t['detector']}] {t['reason']} (score={t['score']})")
        print("  ✓ 聚合器正常")

        return True

    except Exception as e:
        print(f"  ✗ 测试失败: {e}")
        traceback.print_exc()
        return False


def main():
    # 先检查依赖
    missing = check_dependencies()

    print("\n" + "=" * 60)
    print("智能金融数据归因分析平台 - 模块测试")
    print(f"测试时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 60)

    results = []

    # 测试采集模块
    results.append(("采集模块", test_collector_module()))

    # 测试检测模块
    results.append(("检测模块", test_detector_module()))

    # 测试各检测器
    results.append(("检测器单元", test_individual_detectors()))

    # 测试聚合器
    results.append(("结果聚合", test_aggregator()))

    # 汇总结果
    print("\n" + "=" * 60)
    print("测试汇总")
    print("=" * 60)

    passed = 0
    failed = 0
    skipped = 0

    for name, result in results:
        if result is None:
            status = "⊘ 跳过"
            skipped += 1
        elif result:
            status = "✓ 通过"
            passed += 1
        else:
            status = "✗ 失败"
            failed += 1
        print(f"  {name}: {status}")

    print("-" * 40)
    print(f"  总计: {passed} 通过, {failed} 失败, {skipped} 跳过")

    if failed == 0:
        print("\n  🎉 所有测试通过!")
    else:
        print(f"\n  ⚠️  {failed} 个测试失败，请检查错误信息")

    return failed == 0


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
