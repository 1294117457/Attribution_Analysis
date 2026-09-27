"""广撒网：测试所有可能的数据源，找一个当前能跑通的"""
import subprocess

UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/130.0.0.0 Safari/537.36")

# URL, 描述, 验证关键字
SOURCES = [
    # 东方财富 - push2 系列（最近都被 RST）
    ('https://82.push2.eastmoney.com/api/qt/clist/get?pn=1&pz=5&fs=m:90+t:3+f:!50&fields=f2,f12,f14,f104,f105',
     'EM push2 82'),
    ('https://79.push2.eastmoney.com/api/qt/clist/get?pn=1&pz=5&fs=m:90+t:3+f:!50&fields=f2,f12,f14',
     'EM push2 79'),
    ('https://15.push2.eastmoney.com/api/qt/clist/get?pn=1&pz=5&fs=m:90+t:3+f:!50&fields=f2,f12,f14',
     'EM push2 15'),
    ('https://push2.eastmoney.com/api/qt/clist/get?pn=1&pz=5&fs=m:90+t:3+f:!50&fields=f2,f12,f14',
     'EM push2 main'),

    # 东方财富 - 其他域名（web 域名可能放过）
    ('https://datacenter-web.eastmoney.com/api/data/v1/get?reportName=RPT_GN_BOARDDATA&columns=ALL&pageNumber=1&pageSize=5&sortColumns=BOARD_NAME&sortTypes=1&filter=(MARKET%3D%22SH%22)',
     'EM datacenter'),

    # 同花顺 web
    ('http://q.10jqka.com.cn/thsft/api/v1/concept/list',
     'THSFT v1'),
    ('http://q.10jqka.com.cn/thsft/concept',
     'THSFT concept'),

    # 雪球 - 单股 realtime 能过，概念试试
    ('https://stock.xueqiu.com/v5/stock/realtime/quotec.json?symbol=BK0639',
     'XQ realtime BK0639'),

    # 腾讯 - web.ifzq
    ('https://web.ifzq.gtimg.cn/appstock/app/fqkline/get?param=conceptionNumber,conceptionName',
     'QQ fqkline'),

    # 新浪
    ('https://vip.stock.finance.sina.com.cn/quotes_service/api/json_v2.php/Market_Center.getHQNodeData?node=gn_3000&num=5',
     'Sina gn_3000'),

    # 财联社
    ('https://www.cls.cn/telegraph',
     'CLS'),
]


def try_curl(url, timeout=10):
    """直接用 curl.exe 测"""
    try:
        r = subprocess.run(
            ['curl.exe', '-s', '-k', '-A', UA, '-w', '|HTTP=%{http_code}|TIME=%{time_total}', url],
            capture_output=True, text=True, timeout=timeout,
        )
        body = r.stdout
        ok = 'HTTP=200' in body and ('"rc":0' in body or '"data":' in body or 'total' in body or '"code"' in body)
        print(f'  [curl]  {"OK" if ok else "FAIL"} | {body[:150]}')
        return ok
    except Exception as e:
        print(f'  [curl]  ERR {type(e).__name__} {str(e)[:60]}')
        return False


def try_irm(url, timeout=10):
    """用 PowerShell irm 测"""
    try:
        ps = f'(irm "{url}" -UserAgent "{UA}" -TimeoutSec {timeout})'
        r = subprocess.run(
            ['powershell.exe', '-NoProfile', '-Command', ps],
            capture_output=True, text=True, timeout=timeout + 5,
        )
        body = r.stdout
        err = r.stderr
        ok = not err and body and ('"rc":0' in body or '"data":' in body or 'total' in body)
        print(f'  [irm ]  {"OK" if ok else "FAIL"} | {body[:150]}')
        if err and not body:
            print(f'    err[:80]: {err[:80]}')
        return ok
    except Exception as e:
        print(f'  [irm ]  ERR {type(e).__name__} {str(e)[:60]}')
        return False


for url, label in SOURCES:
    print(f'\n[{label}]  {url[:80]}...')
    try_curl(url)
    try_irm(url)
