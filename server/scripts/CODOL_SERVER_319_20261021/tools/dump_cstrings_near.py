from pathlib import Path
p=Path(r'D:\BaiduNetdiskDownload\使命召唤OL\run_codol_001\runs\OMIT_RETEST_20261022\mem\mem_005.bin')
d=p.read_bytes(); base=0x400000
for a in [0xda10e8,0xda10e0,0xda10d8,0xda10c8,0xda10c0,0xda10b0,0xda10a4,0xda109c,0xda1094,0xda1090,0xdafe84,0xdafe7c,0xdafec4,0xdafe6c,0xdafe64,0xdafe54,0xdafe48,0xdafe40,0xdafea4]:
 i=a-base; e=d.find(b'\0',i); print(hex(a),repr(d[i:e].decode('latin1')))
