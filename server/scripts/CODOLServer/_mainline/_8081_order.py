import json,struct,os
p=r'D:\BaiduNetdiskDownload\使命召唤OL\run_codol_001\runs\BEST_8081_STAGE\local_listeners.jsonl'
rows=[json.loads(l) for l in open(p,encoding='utf-8') if l.strip()]
print('event order:')
for i,r in enumerate(rows):
    if r.get('proto')=='udp' and r.get('len'):
        print('  %2d udp:%s len=%d'%(i,r.get('port'),r['len']))
    elif r.get('sent_reply_len'):
        print('  %2d udp:%s SENT_REPLY len=%d'%(i,r.get('port'),r['sent_reply_len']))
    elif r.get('sent_qos_len'):
        print('  %2d udp:%s SENT_QOS len=%d'%(i,r.get('port'),r['sent_qos_len']))
    elif r.get('listen_error') or r.get('bind_error'):
        print('  %2d listen-fail port=%s'%(i,r.get('port')))
print()
for r in rows:
    if r.get('proto')=='udp' and r.get('port')==8081 and r.get('len'):
        d=bytes.fromhex(r['data_hex'])
        print('8081 len=%d first8=%s tail8=%s'%(len(d),d[:8].hex(' '),d[-8:].hex(' ')))
