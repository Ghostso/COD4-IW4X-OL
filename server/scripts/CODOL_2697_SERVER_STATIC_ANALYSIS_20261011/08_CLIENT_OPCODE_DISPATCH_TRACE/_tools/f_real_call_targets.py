
import sys, os, struct
sys.path.insert(0, r'D:\BaiduNetdiskDownload\使命召唤OL\CODOL_2697_SERVER_STATIC_ANALYSIS_20261011\07_PROTOCOL_BIDIRECTIONAL_TRACE\_tools')
import c_common as c
im=c.load()
OUT=r'D:\BaiduNetdiskDownload\使命召唤OL\CODOL_2697_SERVER_STATIC_ANALYSIS_20261011\08_CLIENT_OPCODE_DISPATCH_TRACE\_data'
targets={}
for off in range(0x400,0x400+0x7aca00-5):
    if im.data[off] not in (0xE8,0xE9): continue
    rel=struct.unpack_from('<i',im.data,off+1)[0]
    src=0x401000+(off-0x400)
    tgt=src+5+rel
    if 0x401000 <= tgt < 0x401000+0x7ac90b:
        targets.setdefault(tgt,[]).append(src)
lines=[]
for t in sorted(targets):
    b=im.read_rva(t-0x400000,16)
    tag=''
    if b[:3]==bytes.fromhex('558bec'): tag='PROLOGUE'
    elif b[:1]==b'\x55': tag='PUSH_EBP'
    elif b[:1]==b'\xe9': tag='JMP'
    if tag:
        lines.append('%#x %-8s %s srcs=%s' % (t,tag,b.hex(),[hex(s) for s in targets[t]][:6]))
open(os.path.join(OUT,'f_real_call_targets.txt'),'w',encoding='utf-8').write('\n'.join(lines))
print('\n'.join(lines[:500]))
print('total real targets',len(lines))
