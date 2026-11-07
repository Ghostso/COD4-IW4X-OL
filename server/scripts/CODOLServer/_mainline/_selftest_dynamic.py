import sys, os, json, hashlib
sys.path.insert(0, r'D:\BaiduNetdiskDownload\使命召唤OL\CODOLServer\_mainline')
import engine_dump as E
sent = open(r'D:\BaiduNetdiskDownload\使命召唤OL\run_codol_001\runs\ENGINE_DUMP_20260925_112143\engine\sentinel_table.bin','rb').read()
r = E.derive_runtime_code_range(sent)
print('derive', r)
assert r is not None
print('base=%08x size=%x' % r)
# simulate the runtime JSON payload including protection tuples
payload = {'base': r[0], 'size': r[1], 'sha256': hashlib.sha256(b'x'*r[1]).hexdigest(),
           'protection': [(r[0], r[1], 0x1000, 0x20)]}
s = json.dumps(payload)
print('json_ok', len(s))
print('SELFTEST_OK')
