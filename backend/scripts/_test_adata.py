"""adata 实测 - 看在你机器上能不能跑"""
import sys
import time

print(f'Python: {sys.version}')

try:
    import adata
    print(f'adata 版本: {adata.__version__}')
except Exception as e:
    print(f'adata 导入失败: {e}')
    sys.exit(1)

# 测试 1：单只股票所属概念
print('\n=== 测试 1: get_concept_east(000006) ===')
start = time.time()
try:
    df = adata.stock.info.get_concept_east(stock_code='000006')
    print(f'耗时: {time.time()-start:.2f}s')
    print(f'rows: {len(df)}')
    print(df.head(10).to_string() if len(df) else '<empty>')
except Exception as e:
    print(f'失败: {type(e).__name__}: {e}')
    import traceback
    traceback.print_exc()

# 测试 2：综合接口（行业/地域/概念）
print('\n=== 测试 2: get_plate_east(000006, plate_type=3) ===')
start = time.time()
try:
    df = adata.stock.info.get_plate_east(stock_code='000006', plate_type=3)
    print(f'耗时: {time.time()-start:.2f}s')
    print(f'rows: {len(df)}')
    print(df.head(20).to_string() if len(df) else '<empty>')
except Exception as e:
    print(f'失败: {type(e).__name__}: {e}')
    import traceback
    traceback.print_exc()
