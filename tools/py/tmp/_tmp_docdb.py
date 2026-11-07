import json, socket, sys
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
script = r'''
.echo ===ATTACH===
.reload /f
.echo ===SINGLETON===
dd 0x082E13FC L4
.echo ===STARTED_FLAG===
db 0x0849B61C L4
.echo ===AUTOSTART===
dd 0x0849B7A4 L2
.echo ===ROOMCD===
dd 0x0849B7C4 L2
.echo ===GATEOBJ===
dd poi(0x082E13FC)+0x283 L1
db poi(0x082E13FC)+0x10614 L1
.echo ===DONE===
q
'''
open(r'D:\BaiduNetdiskDownload\使命召唤OL\_tmp_cdb.txt','w',encoding='ascii').write(script)
st = json.load(open(r'CODOLServer\logs\elevated_agent.json'))
argv=['C:\\ich042_tools\\cdb.exe','-p','6532','-cf','D:\\BaiduNetdiskDownload\\使命召唤OL\\_tmp_cdb.txt','-logo','D:\\BaiduNetdiskDownload\\使命召唤OL\\run_codol_001\\logs\\cdb_gate.txt']
req=json.dumps({'token':st['token'],'action':'run','argv':argv,'cwd':r'D:\BaiduNetdiskDownload\使命召唤OL','timeout':120},ensure_ascii=False).encode()+b'\n'
with socket.create_connection(('127.0.0.1',st['port']),timeout=150) as s:
    s.sendall(req); buf=b''
    while not buf.endswith(b'\n'):
        c=s.recv(65536)
        if not c: break
        buf+=c
r=json.loads(buf.decode('utf-8'))
print('rc=',r.get('rc'))
print((r.get('stdout') or '')[:5000])
print('ERR:',(r.get('stderr') or '')[:1000])
