"""
数据采集脚本。
使用模块化的 CollectorService 采集 K 线数据。

用法：
    python scripts/collect_data.py                       # 采集默认股票
    python scripts/collect_data.py 600519 20200101 20250626  # 采集单只股票
    python scripts/collect_data.py --index 000300          # 采集沪深300成分股
    python scripts/collect_data.py --incremental            # 增量采集
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from app.modules.collector.service import CollectorService


# 默认采集的股票列表
DEFAULT_STOCKS = [
    ("600519", "贵州茅台"),
    ("000858", "五粮液"),
    ("000001", "平安银行"),
    ("601318", "中国平安"),
    ("600036", "招商银行"),
]


def main():
    import argparse

    parser = argparse.ArgumentParser(description="数据采集脚本")
    parser.add_argument("code", nargs="?", help="股票代码")
    parser.add_argument("start_date", nargs="?", help="开始日期 YYYYMMDD")
    parser.add_argument("end_date", nargs="?", help="结束日期 YYYYMMDD")
    parser.add_argument("--index", type=str, help="指数代码（如 000300）")
    parser.add_argument("--incremental", action="store_true", help="增量采集")

    args = parser.parse_args()

    service = CollectorService()

    if args.code:
        # 单只股票采集
        code = args.code
        name = code  # 使用代码作为名称
        result = service.collect_single(code, name, args.start_date, args.end_date)

        print("=" * 50)
        print(f"采集 {code} 结果：")
        print(f"  采集数量: {result.collected}")
        print(f"  保存数量: {result.saved}")
        print(f"  状态: {'成功' if result.success else '失败'}")
        if result.error:
            print(f"  错误: {result.error}")
        print("=" * 50)

    elif args.index:
        # 指数成分股采集
        print("=" * 50)
        print(f"开始采集指数 {args.index} 成分股...")
        print("=" * 50)

        result = service.collect_index(args.index, args.start_date, args.end_date)

        print("=" * 50)
        print(f"指数 {args.index} 采集完成：")
        print(f"  总数: {result.total}")
        print(f"  成功: {result.success}")
        print(f"  失败: {result.failed}")
        print(f"  采集数据: {result.total_collected}")
        print(f"  保存数据: {result.total_saved}")
        print("=" * 50)

        # 显示失败列表
        if result.failed > 0:
            failed_list = [r for r in result.results if not r.success]
            if failed_list:
                print("失败列表：")
                for r in failed_list[:5]:
                    print(f"  {r.code}: {r.error}")
                if len(failed_list) > 5:
                    print(f"  ... 还有 {len(failed_list) - 5} 只")

    elif args.incremental:
        # 增量采集
        print("=" * 50)
        print("开始增量采集...")
        print("=" * 50)

        result = service.incremental_collect(DEFAULT_STOCKS)

        print("=" * 50)
        print(f"增量采集完成：")
        print(f"  总数: {result.total}")
        print(f"  成功: {result.success}")
        print(f"  采集数据: {result.total_collected}")
        print(f"  保存数据: {result.total_saved}")
        print("=" * 50)

    else:
        # 默认采集
        print("=" * 50)
        print("开始采集默认股票列表...")
        print(f"股票: {[s[0] for s in DEFAULT_STOCKS]}")
        print("=" * 50)

        result = service.collect_batch(DEFAULT_STOCKS)

        print("=" * 50)
        print(f"采集完成：")
        print(f"  总数: {result.total}")
        print(f"  成功: {result.success}")
        print(f"  失败: {result.failed}")
        print(f"  采集数据: {result.total_collected}")
        print(f"  保存数据: {result.total_saved}")
        print("=" * 50)


if __name__ == "__main__":
    main()
