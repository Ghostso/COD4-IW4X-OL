import json, socket, sys
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
st = json.load(open(r'CODOLServer\logs\elevated_agent.json'))
argv=[sys.executable,'-X','utf8',
      r'D:\BaiduNetdiskDownload\使命召唤OL\_tmp_p1518.py','14696',
      r'D:\BaiduNetdiskDownload\使命召唤OL\run_codol_001\runs\ONCE_20261027_132124\probe_1518.txt']
req=json.dumps({'token':st['token'],'action':'run','argv':argv,'cwd':r'D:\BaiduNetdiskDownload\使命召唤OL','timeout':60},ensure_ascii=False).encode()+b'\n'
with socket.create_connection(('127.0.0.1',st['port']),timeout=90) as s:
    s.sendall(req); buf=b''
    while not buf.endswith(b'\n'):
        c=s.recv(65536)
        if not c: break
        buf+=c
r=json.loads(buf.decode('utf-8'))
print('rc=',r.get('rc'))
print((r.get('stdout') or '')[:1200])
print('ERR:',(r.get('stderr') or '')[:600])
