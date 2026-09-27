"""从 Python 子进程调各种反反爬执行体，验证哪条能过东方财富"""
import subprocess
import json
import sys

URL = ("https://82.push2.eastmoney.com/api/qt/clist/get"
       "?pn=1&pz=5&po=1&np=1&ut=bd1d9ddb04089700cf9c27f6f7426281"
       "&fltt=2&invt=2&fid=f3&fs=m:90+t:3+f:!50"
       "&fields=f2,f3,f12,f14,f104,f105")

UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/130.0.0.0 Safari/537.36")


def try_run(label, cmd, timeout=12):
    try:
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
        body = r.stdout.strip()
        ok = body and '"rc":0' in body
        print(f'\n{label}: rc={r.returncode} bytes={len(body)} ok={ok}')
        print(f'  body[:200]: {body[:200]}')
        if r.stderr:
            print(f'  err[:200]: {r.stderr[:200]}')
        return ok
    except Exception as e:
        print(f'\n{label}: ERR {type(e).__name__} {e}')
        return False


# 1) curl.exe (Windows 自带的)
print('=== 1. curl.exe ===')
try_run('curl.exe -s',
        ['curl.exe', '-s', '-k', '-A', UA, URL])

# 2) powershell.exe + irm
print('\n=== 2. powershell.exe irm ===')
ps_cmd = f'(irm "{URL}" -UserAgent "{UA}" -TimeoutSec 10 | ConvertTo-Json -Depth 3 -Compress)'
try_run('powershell.exe',
        ['powershell.exe', '-NoProfile', '-Command', ps_cmd])

# 3) powershell.exe + HttpClient .NET
print('\n=== 3. powershell.exe HttpClient ===')
ps3 = (
    'Add-Type -AssemblyName System.Net.Http; '
    '$c = New-Object System.Net.Http.HttpClient; '
    f'$c.DefaultRequestHeaders.UserAgent.ParseAdd("{UA}"); '
    f'$r = $c.GetAsync("{URL}").Result; '
    'Write-Output $r.Content.ReadAsStringAsync().Result'
)
try_run('powershell.exe HttpClient',
        ['powershell.exe', '-NoProfile', '-Command', ps3])

# 4) 直接 sys.executable -c 复用 Python（已知会被 RST，做对照）
print('\n=== 4. python sys.executable ===')
py_cmd = (
    'import urllib.request, ssl; '
    'ctx = ssl.create_default_context(); ctx.check_hostname=False; ctx.verify_mode=ssl.CERT_NONE; '
    'req = urllib.request.Request("' + URL + '", headers={"User-Agent":"' + UA + '"}); '
    'r = urllib.request.urlopen(req, timeout=10, context=ctx); '
    'print(r.read().decode("utf-8"))'
)
try_run('python -c', [sys_executable(), '-c', py_cmd] if False else
        ['python', '-c', py_cmd])
