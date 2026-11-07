from pathlib import Path
p=Path(r'D:\BaiduNetdiskDownload\使命召唤OL\run_codol_001\runs\OMIT_RETEST_20261022\mem\mem_005.bin')
d=p.read_bytes()
needles=[b'm4a1tech',b'ak47',b'WeaponDef',b'weaponDef',b'Rechamber',b'rechamber',b'hipSpread',b'HipSpread',b'adsSpread',b'AdsSpread',b'recoil',b'spread',b'gunKick',b'viewKick']
for n in needles:
    hits=[];pos=0
    while True:
        i=d.find(n,pos)
        if i<0: break
        if i==0 or d[i-1]==0 or 32<=d[i-1]<127:
            hits.append(i+0x400000)
        pos=i+1
        if len(hits)>=30: break
    print(n.decode('latin1'),len(hits),[hex(x) for x in hits])
# printable strings of length >=6 containing keywords
runs=[]; start=None
for i,b in enumerate(d):
    if 32<=b<127 or b==9:
        if start is None:start=i
    else:
        if start is not None and i-start>=6:
            s=d[start:i]
            if any(k in s.lower() for k in [b'ads',b'hip',b'spread',b'recoil',b'kick',b'weapon']): runs.append((start+0x400000,s[:200]))
        start=None
print('keyword strings',len(runs))
for a,s in runs[:200]: print(hex(a),s.decode('latin1'))
