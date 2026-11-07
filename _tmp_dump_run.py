import json, socket, sys
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
st = json.load(open(r'CODOLServer\logs\elevated_agent.json'))
argv=[sys.executable,'-X','utf8',
      r'D:\BaiduNetdiskDownload\使命召唤OL\CODOLServer\_mainline\dump_earliest.py',
      r'D:\BaiduNetdiskDownload\使命召唤OL\run_codol_001\runs\EARLIEST_20261027_123806',
      '210','4']
req=json.dumps({'token':st['token'],'action':'run','argv':argv,'cwd':r'D:\BaiduNetdiskDownload\使命召唤OL','timeout':260},ensure_ascii=False).encode()+b'\n'
s=socket.create_connection(('127.0.0.1',st['port']),timeout=300)
s.sendall(req)
print('dumper armed', flush=True)
buf=b''
while not buf.endswith(b'\n'):
    c=s.recv(65536)
    if not c: break
    buf+=c
r=json.loads(buf.decode('utf-8'))
print('rc=',r.get('rc'))
print((r.get('stdout') or '')[:5000])
print('ERR:',(r.get('stderr') or '')[:1500])
