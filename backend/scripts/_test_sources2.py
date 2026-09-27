"""测试更多数据源"""
import requests

HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/130.0.0.0 Safari/537.36',
    'Referer': 'http://www.10jqka.com.cn/',
}


def safe(name, url, params=None, headers=None):
    try:
        r = requests.get(url, params=params or {}, headers=headers or HEADERS, timeout=8, verify=False)
        body = r.text[:300]
        print(f'{name}: {r.status_code} | {body}')
    except Exception as e:
        print(f'{name}: ERR {type(e).__name__} {str(e)[:80]}')


# 同花顺 web - 多个可能的接口
print('=== 同花顺 thsft v2 ===')
safe('thsft_v2_concept', 'http://q.10jqka.com.cn/thsft/api/v2/stock_quotation/concept/list',
     {'page': 1, 'pagesize': 5, 'fields': 'code,name'})
safe('thsft_v2_board', 'http://q.10jqka.com.cn/thsft/api/v2/stock_quotation/board/list',
     {'page': 1, 'pagesize': 5, 'fields': 'code,name'})

print('\n=== 同花顺 问财 ===')
safe('thsft_iwencai', 'http://www.iwencai.com/unifiedwap/unified-wap/result/get-stock-list',
     {'query': '概念板块', 'page': 1, 'per_page': 5})

# 同花顺 数据中心
print('\n=== 同花顺 数据中心 ===')
safe('ths_data_concept', 'http://data.10jqka.com.cn/dataapi/limit_up/continuous_limit_up',
     {'stock': 'all', 'date': '2026-09-26'})

safe('ths_concept_name', 'http://data.10jqka.com.cn/dataapi/stock_block/getBlockName',
     {'type': 'concept'})

# 东方财富 - 备用入口（之前 curl 通的）
print('\n=== 东方财富 备用入口 ===')
safe('em_alt1', 'https://push2.eastmoney.com/api/qt/clist/get',
     {'pn': 1, 'pz': 5, 'po': 1, 'np': 1, 'ut': 'bd1d9ddb04089700cf9c27f6f7426281',
      'fltt': 2, 'invt': 2, 'fid': 'f3', 'fs': 'm:90+t:3+f:!50',
      'fields': 'f1,f2,f3,f4,f8,f12,f14'})

safe('em_82', 'https://82.push2.eastmoney.com/api/qt/clist/get',
     {'pn': 1, 'pz': 5, 'po': 1, 'np': 1, 'ut': 'bd1d9ddb04089700cf9c27f6f7426281',
      'fltt': 2, 'invt': 2, 'fid': 'f3', 'fs': 'm:90+t:3+f:!50',
      'fields': 'f1,f2,f3,f4,f8,f12,f14'})

# 东方财富 - 行情中心 web 接口（备用）
safe('em_quote', 'https://15.push2.eastmoney.com/api/qt/clist/get',
     {'pn': 1, 'pz': 5, 'fs': 'm:90+t:3+f:!50', 'fields': 'f12,f14'})

safe('em_quote_push2', 'https://push2.eastmoney.com/api/qt/clist/get',
     {'pn': 1, 'pz': 5, 'fs': 'm:90+t:3+f:!50', 'fields': 'f12,f14'})

# 备用 - akshare 的 wind / 同花顺 iFinD 备用
print('\n=== 财联社 / 36kr 等 ===')
safe('cls_concept', 'https://www.cls.cn/nodeapi/updateTelegraphList',
     {'app': 'CailianpressWeb', 'category': '', 'lastTime': 0, 'last_time': 0, 'rn': 5})

# 雪球 - 不需登录的概念列表
print('\n=== 雪球 不需登录的 ===')
safe('xueqiu_indu', 'https://stock.xueqiu.com/v5/stock/realtime/quotec.json?symbol=SH000300',
     {})
