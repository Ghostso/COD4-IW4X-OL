import json, collections, struct, os
p=r'D:\BaiduNetdiskDownload\使命召唤OL\run_codol_001\runs\SINGLE_V3\local_listeners.jsonl'
rows=[json.loads(l) for l in open(p,encoding='utf-8') if l.strip()]
pk=[r for r in rows if r.get('proto')=='udp' and r.get('port')==8081]
print('8081 packets',len(pk))
lens=collections.Counter(r['len'] for r in pk)
print('lengths',lens)
for i,r in enumerate(pk):
    d=bytes.fromhex(r['data_hex'])
    print('\n#%d len=%d'%(i,len(d)))
    print(' first16',d[:16].hex(' '))
    print(' last16 ',d[-16:].hex(' '))
    # trailing 4 bytes as u32 be/le
    print(' tail u32be=%08x u32le=%08x'%(struct.unpack('>I',d[-4:])[0],struct.unpack('<I',d[-4:])[0]))
    # entropy-ish top bytes
    print(' byte range',min(d),max(d))
