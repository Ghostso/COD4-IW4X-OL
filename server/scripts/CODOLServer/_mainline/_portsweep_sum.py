import json,os,glob
root=r'D:\BaiduNetdiskDownload\使命召唤OL\run_codol_001\runs'
for d in sorted(glob.glob(os.path.join(root,'PORT_SWEEP_*'))):
    p=os.path.join(d,'local_listeners.jsonl')
    if not os.path.isfile(p): continue
    ev=[json.loads(l) for l in open(p,encoding='utf-8',errors='replace') if l.strip()]
    tq=[r for r in ev if r.get('sent_reply_len')]
    udp=[r for r in ev if r.get('proto')=='udp' and r.get('len')]
    tcp=[r for r in ev if r.get('proto')=='tcp' and r.get('len')]
    print('%-24s tqos_reply=%d udp_in=%s tcp_in=%s'%(
        os.path.basename(d),len(tq),
        sorted(set((r['port'],r['len']) for r in udp)),
        sorted(set(r['port'] for r in tcp))))
