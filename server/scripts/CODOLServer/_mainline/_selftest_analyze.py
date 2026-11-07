import os, struct, subprocess, sys, tempfile
d = tempfile.mkdtemp(prefix='engtest_')
base = 0x00994000
size = 0x1000
buf = bytearray(size)
# fake code: push 0x00CD0100 ; call rel ; mov eax, imm
code = b'\x68\x00\x01\xcd\x00\xe8\x00\x00\x00\x00\xb8\x00\x01\xcd\x00'
buf[0:len(code)] = code
open(os.path.join(d,'engine_best.bin'),'wb').write(bytes(buf))
# runtime_strings window at 0xCD0000
rs = bytearray(0x1000)
msg = b'dwlobbyhost=1.2.3.4\x00blaze.example.qq.com\x00config_mp.cfg\x00'
rs[0x100:0x100+len(msg)] = msg
open(os.path.join(d,'runtime_strings.bin'),'wb').write(bytes(rs))
open(os.path.join(d,'sentinel_table.bin'),'wb').write(b'\x00'*0x1000)
open(os.path.join(d,'dispatch_table.bin'),'wb').write(b'\x00'*0x400)
open(os.path.join(d,'global_state.bin'),'wb').write(b'\x00'*0x1000)
try:
    open(os.path.join(d,'engine_dump.jsonl'),'w').write('{"t":0,"nonzero_bytes":1}\n')
except Exception:
    pass
print('dumpdir', d)
r = subprocess.run([sys.executable,'-X','utf8',r'D:\BaiduNetdiskDownload\使命召唤OL\CODOLServer\_mainline\engine_analyze.py','--dir',d],capture_output=True,text=True)
print('rc',r.returncode)
print(r.stdout)
print(r.stderr)
p = os.path.join(d,'engine_analysis.md')
print('--- report head ---')
print(open(p,encoding='utf-8').read()[:2500])
