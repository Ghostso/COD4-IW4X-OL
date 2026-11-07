import json, socket, sys, threading, time
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
st = json.load(open(r'CODOLServer\logs\elevated_agent.json'))
# 监视器先跑（它自己会轮询等客户端出现）
wargv=[sys.executable,'-X','utf8',
       r'D:\BaiduNetdiskDownload\使命召唤OL\CODOLServer\_mainline\watch_gate_b_early.py',
       r'D:\BaiduNetdiskDownload\使命召唤OL\run_codol_001\logs\gateb_early.txt',
       '240','0.005']
req=json.dumps({'token':st['token'],'action':'run','argv':wargv,'cwd':r'D:\BaiduNetdiskDownload\使命召唤OL','timeout':280},ensure_ascii=False).encode()+b'\n'
s=socket.create_connection(('127.0.0.1',st['port']),timeout=300)
s.sendall(req)
print('watcher launched, waiting...', flush=True)
buf=b''
while not buf.endswith(b'\n'):
    c=s.recv(65536)
    if not c: break
    buf+=c
r=json.loads(buf.decode('utf-8'))
print('rc=',r.get('rc'))
print((r.get('stdout') or '')[:4000])
print('ERR:',(r.get('stderr') or '')[:1200])
