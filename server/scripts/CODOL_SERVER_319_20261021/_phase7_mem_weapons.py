p=r'D:\BaiduNetdiskDownload\使命召唤OL\run_codol_001\runs\OMIT_RETEST_20261022\mem\mem_005.bin'; d=open(p,'rb').read()
for pat in [b'm4a1tech_mp',b'ak47_mp',b'mp5k_mp',b'cheytac_mp',b'weapon_ak47',b'weapon_m4',b'm4a1tech']:
 offs=[]; i=0
 while len(offs)<30:
  i=d.find(pat,i)
  if i<0: break
  offs.append(i);i+=1
 print(pat,len(offs),[hex(x) for x in offs])
