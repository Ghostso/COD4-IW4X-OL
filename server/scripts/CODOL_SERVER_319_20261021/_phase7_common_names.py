import re
p=r'..\run_codol_001\runs\PHASE7_STATIC_20261023\common_mp_zone.bin'; d=open(p,'rb').read()
for lo,hi in [(0x4000,0x6000),(0x30000,0x39000)]:
 print('\n---',hex(lo),hex(hi))
 for m in re.finditer(rb'[ -~]{4,}',d[lo:hi]):
  s=m.group().decode('latin1')
  if any(k in s.lower() for k in ['m4','ak47','weapon','r870','cheytac']): print(hex(lo+m.start()),s[:180])
