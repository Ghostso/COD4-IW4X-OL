p=r'D:\BaiduNetdiskDownload\使命召唤OL\run_codol_001\runs\OMIT_RETEST_20261022\mem\mem_005.bin'
d=open(p,'rb').read()
for pat in [b'fmj_base',b'fmj_shotgun',b'highcal_base',b'weaponattach',b'grip_afgshotgun']:
 offs=[]; i=0
 while len(offs)<20:
  i=d.find(pat,i)
  if i<0: break
  offs.append(i); i+=1
 print(pat,[hex(x) for x in offs])
