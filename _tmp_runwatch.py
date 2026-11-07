import json, socket, sys
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
st = json.load(open(r'CODOLServer\logs\elevated_agent.json'))
argv = [sys.executable, '-X', 'utf8',
        r'D:\BaiduNetdiskDownload\使命召唤OL\CODOLServer\_mainline\watch_gate_b.py',
        '--seconds', '170', '--step', '0.02',
        '--out', r'D:\BaiduNetdiskDownload\使命召唤OL\run_codol_001\logs\gateb_watch.txt']
req = json.dumps({'token': st['token'], 'action': 'run', 'argv': argv,
                  'cwd': r'D:\BaiduNetdiskDownload\使命召唤OL',
                  'timeout': 200}, ensure_ascii=False).encode('utf-8') + b'\n'
print('launching via agent pid=%d port=%d' % (st['pid'], st['port']), flush=True)
with socket.create_connection(('127.0.0.1', st['port']), timeout=230) as s:
    s.sendall(req)
    buf = b''
    while not buf.endswith(b'\n'):
        c = s.recv(65536)
        if not c: break
        buf += c
r = json.loads(buf.decode('utf-8'))
print('ok=', r.get('ok'), 'rc=', r.get('rc'))
print('--- stdout ---')
print((r.get('stdout') or '')[:4000])
print('--- stderr ---')
print((r.get('stderr') or '')[:1500])
