"""API 测试脚本"""
import requests
import time

base = 'http://127.0.0.1:8000/api/v1'

def test_api():
    time.sleep(2)  # 等待服务启动

    # 1. 健康检查
    print('=== 1. 健康检查 ===')
    r = requests.get('http://127.0.0.1:8000/health')
    print(f'状态: {r.json()}')

    # 2. 股票列表（空）
    print('\n=== 2. 股票列表（空）===')
    r = requests.get(f'{base}/stocks/')
    print(f'数量: {r.json()["total"]}')

    # 3. 采集股票
    print('\n=== 3. 采集 000001 ===')
    r = requests.post(f'{base}/stocks/collect', json={'symbol': '000001', 'days': 5})
    result = r.json()
    print(f'状态: {result["status"]} | {result["message"]} | 名称: {result.get("name", "")}')

    # 4. 股票列表
    print('\n=== 4. 股票列表 ===')
    r = requests.get(f'{base}/stocks/')
    data = r.json()
    print(f'总数: {data["total"]}')
    for s in data['items']:
        print(f'   {s["symbol"]} {s["name"]} | {s["record_count"]}条 | {s["kline_start"]}~{s["kline_end"]}')

    # 5. K线数据
    print('\n=== 5. K线数据 ===')
    r = requests.get(f'{base}/stocks/000001/klines', params={'limit': 3})
    klines = r.json()['items']
    for k in klines:
        print(f'   {k["date"]} 收:{k["close"]:.2f} 涨跌:{k["change_pct"] or 0:.2f}%')

    # 6. 删除单条
    kline_to_delete = klines[0]
    print(f'\n=== 6. 删除单条 {kline_to_delete["date"]} ===')
    r = requests.delete(f'{base}/stocks/000001/klines/{kline_to_delete["date"]}')
    print(f'结果: {r.json()}')

    # 7. 最终列表
    print('\n=== 7. 最终股票列表 ===')
    r = requests.get(f'{base}/stocks/')
    data = r.json()
    for s in data['items']:
        print(f'   {s["symbol"]} {s["name"]} | {s["record_count"]}条')

    print('\n✅ API 测试完成')

if __name__ == '__main__':
    test_api()
