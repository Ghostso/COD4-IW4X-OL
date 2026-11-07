from pathlib import Path
import sys
sys.stdout.reconfigure(encoding='utf-8',errors='replace')
p=Path(r'COD OL\WeGameLauncher\launcher.exe')
b=p.read_bytes()
# section VA/file offsets from prior parse
sections=[('.text',0x1000,0x166129,0x400),('.rdata',0x168000,0x64236,0x166600),('.data',0x1cd000,0x2da00,0x1caa00),('.rsrc',0x1fb000,0xc1dd0,0x1e1c00)]
base=0x400000
def off_for(va):
 r=va-base
 for n,v,s,f in sections:
  if v<=r<v+s: return f+(r-v)
 raise ValueError(hex(va))
for va in [0x56f574,0x56f534,0x56f528,0x56f51c,0x56f50c,0x56f4f4,0x56f500,0x56f596,0x56a230,0x5690bc,0x56f1d0]:
 off=off_for(va)
 print(f'VA {va:08X} FILE {off:08X}')
 for enc in ('latin1','utf-16le'):
  s=b[off:off+320].decode(enc,errors='replace')
  cut=s.split('\x00')[0][:200]
  print(enc,repr(cut))
 print(b[off:off+96].hex(' '))
